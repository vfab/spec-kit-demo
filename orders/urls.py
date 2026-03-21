"""URL routing for the orders app."""

from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path(
        "cart/add/<int:product_id>/", views.AddToCartView.as_view(), name="add_to_cart"
    ),
    path(
        "cart/remove/<int:item_id>/",
        views.RemoveFromCartView.as_view(),
        name="remove_from_cart",
    ),
    path(
        "cart/update/<int:item_id>/", views.UpdateCartView.as_view(), name="update_cart"
    ),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path(
        "checkout/confirmation/<str:order_number>/",
        views.OrderConfirmationView.as_view(),
        name="order_confirmation",
    ),
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path(
        "orders/<str:order_number>/",
        views.OrderDetailView.as_view(),
        name="order_detail",
    ),
]
