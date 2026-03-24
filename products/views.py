from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Avg, Case, Count, IntegerField, Max, Min, Q, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, FormView, ListView, TemplateView, View

from .forms import ReviewSubmissionForm
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

    def _base_queryset(self):
        """Filtered product queryset without the approved_review_count annotation.

        Used for aggregates (price range) that don't need the reviews JOIN so
        those queries don't pay for an unnecessary GROUP BY.
        """
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

    def get_queryset(self):
        return self._base_queryset().annotate(
            approved_review_count=Count(
                "reviews", filter=Q(reviews__is_approved=True)
            )
        )

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

        # Price range for filter — use the base (un-annotated) queryset so
        # the aggregate doesn't pay for the approved_review_count JOIN (L2).
        price_range = self._base_queryset().aggregate(
            min_price=Min("price"), max_price=Max("price")
        )
        context["price_range"] = price_range

        # Recently viewed shelf (T029) — read-only, no session mutation here
        rv_pks = self.request.session.get("recently_viewed", [])
        if rv_pks:
            rv_map = {
                p.pk: p
                for p in Product.objects.filter(pk__in=rv_pks, is_active=True)
                .select_related("category")
                .prefetch_related("images")
                .annotate(
                    approved_review_count=Count(
                        "reviews", filter=Q(reviews__is_approved=True)
                    )
                )
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
        return (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("images", "variants")
            .annotate(
                review_count=Count(
                    "reviews", filter=Q(reviews__is_approved=True)
                ),
                avg_rating=Avg(
                    "reviews__rating", filter=Q(reviews__is_approved=True)
                ),
            )
        )

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

        # Product images and variants — use prefetched data from get_queryset()
        # to stay within the intended query budget for this view.
        context["images"] = product.images.all()
        # Filter in Python so the .filter() call doesn't bypass the prefetch cache.
        context["variants"] = [v for v in product.variants.all() if v.is_active]

        # Approved reviews — list for display (T008).
        # Aggregate counts/average are annotated on the product queryset in
        # get_queryset() so no separate aggregate() query is needed here.
        context["reviews"] = ProductReview.objects.filter(
            product=product, is_approved=True
        ).select_related("user")
        context["review_count"] = product.review_count or 0
        avg = product.avg_rating
        context["avg_rating"] = round(avg, 1) if avg else None
        context["rounded_avg_rating"] = round(avg) if avg else 0

        context["review_form"] = ReviewSubmissionForm()

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
                .select_related("category")
                .prefetch_related("images")
                .annotate(
                    approved_review_count=Count(
                        "reviews", filter=Q(reviews__is_approved=True)
                    )
                )
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
            .annotate(
                approved_review_count=Count(
                    "reviews", filter=Q(reviews__is_approved=True)
                )
            )
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
    ALLOWED_SORT_FIELDS = {
        "-created_at",
        "created_at",
        "price",
        "-price",
        "name",
        "-name",
    }

    def get_queryset(self):
        query = self.request.GET.get("q", "")
        if query:
            sort_by = self.request.GET.get("sort", "-created_at")
            if sort_by not in self.ALLOWED_SORT_FIELDS:
                sort_by = "-created_at"
            return (
                Product.objects.filter(
                    Q(name__icontains=query)
                    | Q(description__icontains=query)
                    | Q(category__name__icontains=query),
                    is_active=True,
                )
                .select_related("category")
                .annotate(
                    approved_review_count=Count(
                        "reviews", filter=Q(reviews__is_approved=True)
                    )
                )
                .distinct()
                .order_by(sort_by)
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
        if len(q) < 2 or len(q) > 100:
            return JsonResponse({"results": []})
        products = Product.objects.filter(name__icontains=q, is_active=True).only(
            "name", "slug"
        )[:10]
        results = [{"name": p.name, "url": p.get_absolute_url()} for p in products]
        return JsonResponse({"results": results})


class ReviewSubmitView(LoginRequiredMixin, FormView):
    """Handle review submission for a product (T021).

    Only POST is accepted — the form is rendered inside product_detail.html,
    never via a direct GET to this URL.
    """

    http_method_names = ["post", "options"]

    def get_form_class(self):
        return ReviewSubmissionForm

    def get_product(self):
        # Must use ProductDetailView's annotated queryset so the product object
        # carries review_count and avg_rating; get_object_or_404 on un-annotated
        # Product would cause AttributeError when get_context_data accesses them.
        return get_object_or_404(
            ProductDetailView().get_queryset(), slug=self.kwargs["slug"]
        )

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
        # Re-render the product detail page with the full ProductDetailView
        # context so that no template sections are missing.
        product = self.get_product()
        detail_view = ProductDetailView()
        detail_view.request = self.request
        detail_view.kwargs = self.kwargs
        detail_view.object = product
        context = detail_view.get_context_data(object=product)
        context["review_form"] = form
        return render(self.request, "products/product_detail.html", context)


def _redirect_with_error(referrer, error_code):
    """Return a redirect to referrer with compare_error safely appended.

    Uses urllib.parse to merge the parameter so existing query strings
    like ?category=1 become ?category=1&compare_error=limit rather than
    ?category=1?compare_error=limit.
    """
    parsed = urlparse(referrer)
    # Build a fresh query dict preserving existing params, then add/replace error.
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["compare_error"] = [error_code]
    new_query = urlencode(params, doseq=True)
    new_url = str(urlunparse(parsed._replace(query=new_query)))
    return redirect(new_url)


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
            return _redirect_with_error(referrer, "invalid")

        product = get_object_or_404(Product, pk=product_id, is_active=True)

        comparison = request.session.get("comparison", {"pks": [], "category_id": None, "items": []})
        pks = comparison.get("pks", [])
        category_id = comparison.get("category_id")
        items = comparison.get("items", [])

        # Already in list — no-op
        if product_id in pks:
            return redirect(referrer)

        # Enforce same-category constraint
        if category_id is not None and product.category_id != category_id:
            return _redirect_with_error(referrer, "category")

        # Enforce 3-product limit
        if len(pks) >= 3:
            return _redirect_with_error(referrer, "limit")

        pks.append(product_id)
        items.append({"pk": product_id, "name": product.name})
        request.session["comparison"] = {
            "pks": pks,
            "category_id": product.category_id,
            "items": items,
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
            request.session["comparison"] = {"pks": [], "category_id": None, "items": []}
            request.session.modified = True
            return redirect(referrer)

        try:
            product_id = int(product_id_raw)
        except (ValueError, TypeError):
            return redirect(referrer)

        comparison = request.session.get("comparison", {"pks": [], "category_id": None, "items": []})
        pks = [p for p in comparison.get("pks", []) if p != product_id]
        items = [item for item in comparison.get("items", []) if item["pk"] != product_id]
        request.session["comparison"] = {
            "pks": pks,
            "category_id": comparison.get("category_id") if pks else None,
            "items": items,
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
        # Use Case/When to preserve the session-defined order while returning
        # a real QuerySet (so ListView internals work correctly).
        ordering = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(pks)],
            output_field=IntegerField(),
        )
        return (
            Product.objects.filter(pk__in=pks, is_active=True)
            .prefetch_related("images", "variants")
            .annotate(
                _order=ordering,
                approved_review_count=Count(
                    "reviews", filter=Q(reviews__is_approved=True)
                ),
            )
            .order_by("_order")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        compared = list(context["compared_products"])

        # Build attribute matrix as a list of (attr_name, [values_per_product]) rows
        # so templates can iterate without needing a custom filter.
        attr_order: list[str] = []
        attr_index: dict[str, int] = {}
        rows: list[list[list[str]]] = []  # rows[attr_idx][product_idx] = [values]

        for prod_idx, product in enumerate(compared):
            # Iterate the prefetched variants and filter in Python to avoid
            # an extra DB query per product (N+1) from .filter() bypassing cache.
            for variant in product.variants.all():
                if not variant.is_active:
                    continue
                if variant.name not in attr_index:
                    attr_index[variant.name] = len(attr_order)
                    attr_order.append(variant.name)
                    rows.append([[] for _ in compared])
                row_idx = attr_index[variant.name]
                rows[row_idx][prod_idx].append(variant.value)

        # Zip into (name, [per-product values]) for easy template iteration
        context["attribute_rows"] = list(zip(attr_order, rows))
        return context
