"""Management command to add sample cart data for development and testing."""

import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from orders.models import Cart, CartItem
from products.models import Product, ProductVariant


class Command(BaseCommand):
    help = "Add sample cart items for testing"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample cart items...")

        # Get sample users
        users = User.objects.filter(is_superuser=False)
        products = Product.objects.filter(is_active=True)

        if not users.exists():
            self.stdout.write(
                self.style.ERROR("No sample users found. Run create_sample_data first.")
            )
            return

        for user in users:
            # Create or get cart for user
            cart, created = Cart.objects.get_or_create(user=user)

            # Add 2-4 random products to cart
            num_items = random.randint(2, 4)
            sample_products = random.sample(
                list(products), min(num_items, len(products))
            )

            for product in sample_products:
                # Check if product has variants
                variants = ProductVariant.objects.filter(
                    product=product, stock_quantity__gt=0
                )
                if variants.exists():
                    # Use a random variant
                    variant = random.choice(variants)
                    quantity = random.randint(1, min(3, variant.stock_quantity))

                    cart_item, created = CartItem.objects.get_or_create(
                        cart=cart,
                        product=product,
                        variant=variant,
                        defaults={"quantity": quantity},
                    )
                else:
                    # Use product without variant
                    if product.stock_quantity > 0:
                        quantity = random.randint(1, min(3, product.stock_quantity))

                        cart_item, created = CartItem.objects.get_or_create(
                            cart=cart, product=product, defaults={"quantity": quantity}
                        )

                if created:
                    self.stdout.write(
                        f"  Added {product.name} to {user.username}'s cart"
                    )

        # Display cart summary
        self.stdout.write("\n=== Cart Summary ===")
        for cart in Cart.objects.all():
            if cart.user:
                self.stdout.write(
                    f"{cart.user.username}: {cart.total_items} items,"
                    f" ${cart.total_price:.2f}"
                )

        self.stdout.write(self.style.SUCCESS("Sample cart items created successfully!"))
