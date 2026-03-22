from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Avg, Max, Min, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, FormView, ListView, TemplateView, View

from .models import Category, Product, ProductReview


class HomeView(TemplateView):
    """Home page view"""

    template_name = "products/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Cache featured products and categories together under a single key
        # to minimise per-request DB hits on the busiest page.
        cached = cache.get("home_page_data")
        if cached is None:
            featured = list(
                Product.objects.filter(is_active=True, is_featured=True).select_related(
                    "category"
                )[:8]
            )
            categories = list(Category.objects.filter(parent=None)[:6])
            cached = {"featured_products": featured, "categories": categories}
            cache.set(
                "home_page_data",
                cached,
                timeout=getattr(settings, "CACHE_TIMEOUT_PRODUCT_LIST", 300),
            )

        context["featured_products"] = cached["featured_products"]
        context["categories"] = cached["categories"]
        return context


class ProductListView(ListView):
    """List all products with filtering and pagination"""

    model = Product
    template_name = "products/product_list.html"
    context_object_name = "products"
    paginate_by = 12
    # R6: Class-level constant so the set is built once, not on every request.
    ALLOWED_SORT_FIELDS = {
        "-created_at",
        "created_at",
        "price",
        "-price",
        "name",
        "-name",
    }

    def get_queryset(self):
        queryset = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("images", "variants")
        )

        # Search filter
        search = self.request.GET.get("search") or self.request.GET.get("q")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(slug__icontains=search)
            )

        # Category filter - accept either slug or id
        category_param = self.request.GET.get("category")
        if category_param:
            if str(category_param).isdigit():
                category = get_object_or_404(Category, id=category_param)
            else:
                category = get_object_or_404(Category, slug=category_param)
            queryset = queryset.filter(
                Q(category=category) | Q(category__parent=category)
            )

        # Price filter — validate as numeric before passing to ORM to avoid
        # unhandled ValidationError on non-numeric (e.g. injection) input.
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        try:
            if min_price:
                queryset = queryset.filter(price__gte=float(min_price))
        except (ValueError, TypeError):
            pass  # silently ignore non-numeric input
        try:
            if max_price:
                queryset = queryset.filter(price__lte=float(max_price))
        except (ValueError, TypeError):
            pass  # silently ignore non-numeric input

        # Sort by: validated against ALLOWED_SORT_FIELDS allowlist (M3)
        sort_by = self.request.GET.get("sort", "-created_at")
        if sort_by not in self.ALLOWED_SORT_FIELDS:
            sort_by = "-created_at"
        queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Cache the category list (changes rarely).
        categories = cache.get("product_categories")
        if categories is None:
            categories = list(Category.objects.filter(parent=None))
            cache.set(
                "product_categories",
                categories,
                timeout=getattr(settings, "CACHE_TIMEOUT_CATEGORY_LIST", 900),
            )
        context["categories"] = categories

        # Price range for filter — use the active queryset so bounds
        # reflect any applied category/search filters (L2).
        price_range = self.get_queryset().aggregate(
            min_price=Min("price"), max_price=Max("price")
        )
        context["price_range"] = price_range

        # Recently viewed shelf (T029) — read-only, no session mutation here
        rv_pks = self.request.session.get("recently_viewed", [])
        if rv_pks:
            rv_map = {
                p.pk: p
                for p in Product.objects.filter(pk__in=rv_pks, is_active=True)
                .only("name", "slug", "price")
                .prefetch_related("images")
            }
            context["recently_viewed"] = [rv_map[pk] for pk in rv_pks if pk in rv_map]
        else:
            context["recently_viewed"] = []

        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get("format") == "partial":
            self.template_name = "products/_product_grid.html"
        return super().render_to_response(context, **response_kwargs)


class ProductDetailView(DetailView):
    """Product detail view"""

    model = Product
    template_name = "products/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category")

    def get_object(self, queryset=None):
        """Return the product, using the cache when available.

        Checks the cache BEFORE issuing any DB query so that cache hits
        truly avoid a round-trip to the database.
        """
        if queryset is None:
            queryset = self.get_queryset()

        # Build a slug-based cache key for the pre-DB cache check.
        # The canonical key is pk-based (set on first load); the slug key
        # is an alias that stores the pk so we can redirect to the pk key.
        slug = self.kwargs.get(self.slug_url_kwarg)
        slug_cache_key = f"product_detail_slug:{slug}" if slug else None

        # Fast path: pk already known from a previous request
        if slug_cache_key:
            cached_pk = cache.get(slug_cache_key)
            if cached_pk is not None:
                pk_cache_key = f"product_detail:{cached_pk}"
                cached_obj = cache.get(pk_cache_key)
                if cached_obj is not None:
                    return cached_obj

        # Slow path: resolve via ORM, then warm both cache keys.
        obj = super().get_object(queryset=queryset)
        pk_cache_key = f"product_detail:{obj.pk}"
        timeout = getattr(settings, "CACHE_TIMEOUT_PRODUCT_DETAIL", 600)
        cache.set(pk_cache_key, obj, timeout=timeout)
        if slug_cache_key:
            cache.set(slug_cache_key, obj.pk, timeout=timeout)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # Related products
        context["related_products"] = (
            Product.objects.filter(category=product.category, is_active=True)
            .select_related("category")
            .exclude(id=product.id)[:4]
        )

        # Product images and variants — prefetched to avoid per-image DB hits
        context["images"] = product.images.all()
        context["variants"] = product.variants.filter(stock_quantity__gt=0)

        # Approved reviews with aggregate rating (T008)
        reviews = ProductReview.objects.filter(
            product=product, is_approved=True
        ).select_related("user")
        context["reviews"] = reviews
        context["review_count"] = reviews.count()
        avg = reviews.aggregate(avg_rating=Avg("rating"))["avg_rating"]
        context["avg_rating"] = round(avg, 1) if avg else None

        # Review form — lazy import to avoid circular dep; None if not yet available
        try:
            from .forms import ReviewSubmissionForm  # noqa: PLC0415

            context["review_form"] = ReviewSubmissionForm()
        except ImportError:
            context["review_form"] = None

        # Current user's existing review (None for anonymous users)
        if self.request.user.is_authenticated:
            context["user_existing_review"] = ProductReview.objects.filter(
                product=product, user=self.request.user
            ).first()
        else:
            context["user_existing_review"] = None

        # Recently viewed — session tracking (T027)
        recently_viewed_pks = self.request.session.get("recently_viewed", [])
        pk = product.pk
        # Deduplicate and prepend current product
        recently_viewed_pks = [p for p in recently_viewed_pks if p != pk]
        recently_viewed_pks.insert(0, pk)
        recently_viewed_pks = recently_viewed_pks[:8]
        self.request.session["recently_viewed"] = recently_viewed_pks
        self.request.session.modified = True

        # Batch-fetch recently viewed products (excluding current)
        rv_pks = [p for p in recently_viewed_pks if p != pk]
        if rv_pks:
            rv_map = {
                p.pk: p
                for p in Product.objects.filter(pk__in=rv_pks, is_active=True)
                .only("name", "slug", "price")
                .prefetch_related("images")
            }
            # Preserve session order
            context["recently_viewed"] = [rv_map[p] for p in rv_pks if p in rv_map]
        else:
            context["recently_viewed"] = []

        return context


class CategoryView(ListView):
    """Category-specific product view"""

    model = Product
    template_name = "products/category.html"
    context_object_name = "products"
    paginate_by = 12
    ALLOWED_SORT_FIELDS = {
        "-created_at",
        "created_at",
        "price",
        "-price",
        "name",
        "-name",
    }

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["slug"])
        queryset = (
            Product.objects.filter(
                Q(category=self.category) | Q(category__parent=self.category),
                is_active=True,
            )
            .select_related("category")
            .prefetch_related("images", "variants")
        )
        sort_by = self.request.GET.get("sort", "-created_at")
        if sort_by not in self.ALLOWED_SORT_FIELDS:
            sort_by = "-created_at"
        return queryset.order_by(sort_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        context["subcategories"] = self.category.children.filter(is_active=True)
        return context


class ProductSearchView(ListView):
    """Product search view"""

    model = Product
    template_name = "products/search_results.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        query = self.request.GET.get("q", "")
        if query:
            return (
                Product.objects.filter(
                    Q(name__icontains=query)
                    | Q(description__icontains=query)
                    | Q(category__name__icontains=query),
                    is_active=True,
                )
                .select_related("category")
                .distinct()
            )
        return Product.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context


class AutocompleteView(View):
    """JSON autocomplete endpoint for the search input (T012)."""

    def get(self, request):
        q = request.GET.get("q", "").strip()
        if len(q) < 2:
            return JsonResponse({"results": []})
        products = (
            Product.objects.filter(name__icontains=q, is_active=True)
            .only("name", "slug")[:10]
        )
        results = [{"name": p.name, "url": p.get_absolute_url()} for p in products]
        return JsonResponse({"results": results})


class ReviewSubmitView(LoginRequiredMixin, FormView):
    """Handle review submission for a product (T021).

    Only POST is accepted — the form is rendered inside product_detail.html,
    never via a direct GET to this URL.
    """

    http_method_names = ["post", "options"]

    def get_form_class(self):
        from .forms import ReviewSubmissionForm  # noqa: PLC0415

        return ReviewSubmissionForm

    def get_product(self):
        return get_object_or_404(Product, slug=self.kwargs["slug"], is_active=True)

    def form_valid(self, form):
        product = self.get_product()
        if ProductReview.objects.filter(
            product=product, user=self.request.user
        ).exists():
            return redirect(
                reverse("products:product_detail", kwargs={"slug": product.slug})
                + "?review=exists"
            )
        review = form.save(commit=False)
        review.product = product
        review.user = self.request.user
        review.is_approved = False
        review.save()
        return redirect(
            reverse("products:product_detail", kwargs={"slug": product.slug})
            + "?review=submitted"
        )

    def form_invalid(self, form):
        # Re-render the product detail page with form errors
        product = self.get_product()
        from django.shortcuts import render  # noqa: PLC0415

        reviews = ProductReview.objects.filter(
            product=product, is_approved=True
        ).select_related("user")
        return render(
            self.request,
            "products/product_detail.html",
            {
                "product": product,
                "review_form": form,
                "reviews": reviews,
                "review_count": reviews.count(),
                "images": product.images.all(),
                "variants": product.variants.filter(stock_quantity__gt=0),
            },
        )


class ComparisonAddView(View):
    """Add a product to the session-based comparison list (T031)."""

    def post(self, request):
        referrer = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")
        # Open-redirect guard
        if not url_has_allowed_host_and_scheme(
            referrer,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            referrer = "/"

        try:
            product_id = int(request.POST.get("product_id", ""))
        except (ValueError, TypeError):
            return redirect(referrer + "?compare_error=invalid")

        product = get_object_or_404(Product, pk=product_id, is_active=True)

        comparison = request.session.get(
            "comparison", {"pks": [], "category_id": None}
        )
        pks = comparison.get("pks", [])
        category_id = comparison.get("category_id")

        # Already in list — no-op
        if product_id in pks:
            return redirect(referrer)

        # Enforce same-category constraint
        if category_id is not None and product.category_id != category_id:
            return redirect(referrer + "?compare_error=category")

        # Enforce 3-product limit
        if len(pks) >= 3:
            return redirect(referrer + "?compare_error=limit")

        pks.append(product_id)
        request.session["comparison"] = {
            "pks": pks,
            "category_id": product.category_id,
        }
        request.session.modified = True
        return redirect(referrer)


class ComparisonRemoveView(View):
    """Remove a product from the session comparison list (T031)."""

    def post(self, request):
        referrer = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")
        if not url_has_allowed_host_and_scheme(
            referrer,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            referrer = "/"

        product_id_raw = request.POST.get("product_id", "")

        # "clear" sentinel: wipe the entire comparison list at once.
        if product_id_raw == "clear":
            request.session["comparison"] = {"pks": [], "category_id": None}
            request.session.modified = True
            return redirect(referrer)

        try:
            product_id = int(product_id_raw)
        except (ValueError, TypeError):
            return redirect(referrer)

        comparison = request.session.get("comparison", {"pks": [], "category_id": None})
        pks = [p for p in comparison.get("pks", []) if p != product_id]
        request.session["comparison"] = {
            "pks": pks,
            "category_id": comparison.get("category_id") if pks else None,
        }
        request.session.modified = True
        return redirect(referrer)


class ComparisonView(ListView):
    """Display the side-by-side product comparison page (T031)."""

    template_name = "products/compare.html"
    context_object_name = "compared_products"

    def get_queryset(self):
        comparison = self.request.session.get("comparison", {"pks": []})
        pks = comparison.get("pks", [])
        if not pks:
            return Product.objects.none()
        products = Product.objects.filter(pk__in=pks, is_active=True).prefetch_related(
            "images", "variants"
        )
        # Preserve session order
        pk_map = {p.pk: p for p in products}
        return [pk_map[pk] for pk in pks if pk in pk_map]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        compared = context["compared_products"]

        # Build attribute matrix as a list of (attr_name, [values_per_product]) rows
        # so templates can iterate without needing a custom filter.
        attr_order: list[str] = []
        attr_index: dict[str, int] = {}
        rows: list[list[list[str]]] = []  # rows[attr_idx][product_idx] = [values]

        for product in compared:
            for variant in product.variants.all():
                if variant.name not in attr_index:
                    attr_index[variant.name] = len(attr_order)
                    attr_order.append(variant.name)
                    rows.append([[] for _ in compared])
                row_idx = attr_index[variant.name]
                prod_idx = list(compared).index(product)
                rows[row_idx][prod_idx].append(variant.value)

        # Zip into (name, [per-product values]) for easy template iteration
        context["attribute_rows"] = list(zip(attr_order, rows))
        return context
