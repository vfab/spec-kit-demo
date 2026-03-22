"""URL routing for the products app."""

from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("products/", views.ProductListView.as_view(), name="product_list"),
    # Autocomplete must be before the <slug> pattern (T012)
    path(
        "products/autocomplete/",
        views.AutocompleteView.as_view(),
        name="autocomplete",
    ),
    # Comparison routes must be before the <slug> pattern (T032)
    path("products/compare/", views.ComparisonView.as_view(), name="compare"),
    path(
        "products/compare/add/",
        views.ComparisonAddView.as_view(),
        name="compare_add",
    ),
    path(
        "products/compare/remove/",
        views.ComparisonRemoveView.as_view(),
        name="compare_remove",
    ),
    # Review submission — also before the generic <slug> detail route (T022)
    path(
        "products/<slug:slug>/review/",
        views.ReviewSubmitView.as_view(),
        name="submit_review",
    ),
    path(
        "products/<slug:slug>/",
        views.ProductDetailView.as_view(),
        name="product_detail",
    ),
    path("category/<slug:slug>/", views.CategoryView.as_view(), name="category"),
    path("search/", views.ProductSearchView.as_view(), name="search"),
]
