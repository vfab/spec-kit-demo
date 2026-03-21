from django.conf import settings
from django.core.cache import cache
from django.db.models import Max, Min, Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView, TemplateView

from .models import Category, Product


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

        return context


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

        return context


class CategoryView(ListView):
    """Category-specific product view"""

    model = Product
    template_name = "products/category.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["slug"])
        return (
            Product.objects.filter(
                Q(category=self.category) | Q(category__parent=self.category),
                is_active=True,
            )
            .select_related("category")
            .prefetch_related("images", "variants")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
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
