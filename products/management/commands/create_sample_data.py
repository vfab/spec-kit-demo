"""Management command to create sample products, categories, and users."""

import random
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from accounts.models import UserProfile
from products.models import Category, Product, ProductVariant


class Command(BaseCommand):
    help = "Create sample data for the e-commerce site"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before creating new sample data",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            ProductVariant.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            UserProfile.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        self.stdout.write("Creating sample data...")

        # Create categories
        categories = self.create_categories()

        # Create products for each category
        self.create_products(categories)

        # Create sample users
        self.create_sample_users()

        self.stdout.write(self.style.SUCCESS("Successfully created sample data!"))

    def create_categories(self):
        """Create sample categories"""
        self.stdout.write("Creating categories...")

        categories_data = [
            {
                "name": "Electronics",
                "description": "Latest electronic devices and gadgets",
                "subcategories": [
                    {
                        "name": "Smartphones",
                        "description": "Latest smartphones and mobile devices",
                    },
                    {
                        "name": "Laptops",
                        "description": "Laptops and notebooks for work and gaming",
                    },
                    {
                        "name": "Audio",
                        "description": "Headphones, speakers, and audio equipment",
                    },
                    {
                        "name": "Gaming",
                        "description": "Gaming consoles and accessories",
                    },
                ],
            },
            {
                "name": "Fashion",
                "description": "Trendy clothing and accessories",
                "subcategories": [
                    {"name": "Men's Clothing", "description": "Clothing for men"},
                    {"name": "Women's Clothing", "description": "Clothing for women"},
                    {"name": "Shoes", "description": "Footwear for all occasions"},
                    {
                        "name": "Accessories",
                        "description": "Fashion accessories and jewelry",
                    },
                ],
            },
            {
                "name": "Home & Garden",
                "description": "Everything for your home and garden",
                "subcategories": [
                    {"name": "Furniture", "description": "Home and office furniture"},
                    {
                        "name": "Kitchen",
                        "description": "Kitchen appliances and utensils",
                    },
                    {"name": "Decor", "description": "Home decoration and accessories"},
                    {"name": "Garden", "description": "Gardening tools and supplies"},
                ],
            },
            {
                "name": "Sports & Outdoors",
                "description": "Sports equipment and outdoor gear",
                "subcategories": [
                    {"name": "Fitness", "description": "Fitness equipment and gear"},
                    {
                        "name": "Outdoor Recreation",
                        "description": "Camping, hiking, and outdoor gear",
                    },
                    {
                        "name": "Sports Equipment",
                        "description": "Equipment for various sports",
                    },
                    {
                        "name": "Athletic Wear",
                        "description": "Sportswear and athletic clothing",
                    },
                ],
            },
        ]

        categories = {}
        for cat_data in categories_data:
            # Create parent category
            parent = Category.objects.create(
                name=cat_data["name"],
                slug=slugify(cat_data["name"]),
                description=cat_data["description"],
                is_active=True,
            )
            categories[parent.name] = parent
            self.stdout.write(f"  Created category: {parent.name}")

            # Create subcategories
            for subcat_data in cat_data["subcategories"]:
                subcategory = Category.objects.create(
                    name=subcat_data["name"],
                    slug=slugify(subcat_data["name"]),
                    description=subcat_data["description"],
                    parent=parent,
                    is_active=True,
                )
                categories[subcategory.name] = subcategory
                self.stdout.write(f"    Created subcategory: {subcategory.name}")

        return categories

    def create_products(self, categories):
        """Create sample products"""
        self.stdout.write("Creating products...")

        products_data = {
            "Smartphones": [
                {
                    "name": "iPhone 15 Pro",
                    "description": "Latest iPhone with advanced camera system"
                    " and titanium design.",
                    "price": Decimal("999.00"),
                    "variants": [
                        {
                            "name": "Storage",
                            "value": "128GB",
                            "price_adjustment": 0,
                            "stock": 50,
                        },
                        {
                            "name": "Storage",
                            "value": "256GB",
                            "price_adjustment": 200,
                            "stock": 30,
                        },
                        {
                            "name": "Storage",
                            "value": "512GB",
                            "price_adjustment": 400,
                            "stock": 15,
                        },
                    ],
                },
                {
                    "name": "Samsung Galaxy S24",
                    "description": "Premium Android smartphone with AI-powered"
                    " features.",
                    "price": Decimal("899.00"),
                    "variants": [
                        {
                            "name": "Storage",
                            "value": "128GB",
                            "price_adjustment": 0,
                            "stock": 40,
                        },
                        {
                            "name": "Storage",
                            "value": "256GB",
                            "price_adjustment": 150,
                            "stock": 25,
                        },
                    ],
                },
                {
                    "name": "Google Pixel 8",
                    "description": "Pure Android experience with exceptional"
                    " camera capabilities.",
                    "price": Decimal("699.00"),
                    "variants": [
                        {
                            "name": "Storage",
                            "value": "128GB",
                            "price_adjustment": 0,
                            "stock": 35,
                        },
                        {
                            "name": "Storage",
                            "value": "256GB",
                            "price_adjustment": 100,
                            "stock": 20,
                        },
                    ],
                },
            ],
            "Laptops": [
                {
                    "name": "MacBook Air M3",
                    "description": "Ultra-thin laptop with Apple M3 chip for"
                    " incredible performance.",
                    "price": Decimal("1199.00"),
                    "variants": [
                        {
                            "name": "RAM",
                            "value": "8GB",
                            "price_adjustment": 0,
                            "stock": 25,
                        },
                        {
                            "name": "RAM",
                            "value": "16GB",
                            "price_adjustment": 200,
                            "stock": 15,
                        },
                        {
                            "name": "RAM",
                            "value": "24GB",
                            "price_adjustment": 400,
                            "stock": 8,
                        },
                    ],
                },
                {
                    "name": "Dell XPS 13",
                    "description": "Premium Windows ultrabook with stunning display.",
                    "price": Decimal("999.00"),
                    "variants": [
                        {
                            "name": "Processor",
                            "value": "Intel i5",
                            "price_adjustment": 0,
                            "stock": 20,
                        },
                        {
                            "name": "Processor",
                            "value": "Intel i7",
                            "price_adjustment": 300,
                            "stock": 10,
                        },
                    ],
                },
                {
                    "name": "Gaming Laptop RTX 4070",
                    "description": "High-performance gaming laptop with RTX 4070"
                    " graphics.",
                    "price": Decimal("1599.00"),
                    "variants": [
                        {
                            "name": "RAM",
                            "value": "16GB",
                            "price_adjustment": 0,
                            "stock": 12,
                        },
                        {
                            "name": "RAM",
                            "value": "32GB",
                            "price_adjustment": 300,
                            "stock": 8,
                        },
                    ],
                },
            ],
            "Audio": [
                {
                    "name": "Sony WH-1000XM5",
                    "description": "Premium noise-canceling wireless headphones.",
                    "price": Decimal("399.00"),
                    "variants": [
                        {
                            "name": "Color",
                            "value": "Black",
                            "price_adjustment": 0,
                            "stock": 30,
                        },
                        {
                            "name": "Color",
                            "value": "Silver",
                            "price_adjustment": 0,
                            "stock": 20,
                        },
                    ],
                },
                {
                    "name": "AirPods Pro 2",
                    "description": "Apple's premium wireless earbuds with"
                    " spatial audio.",
                    "price": Decimal("249.00"),
                    "stock": 45,
                },
                {
                    "name": "JBL Charge 5",
                    "description": "Portable Bluetooth speaker with powerful bass.",
                    "price": Decimal("179.00"),
                    "variants": [
                        {
                            "name": "Color",
                            "value": "Black",
                            "price_adjustment": 0,
                            "stock": 25,
                        },
                        {
                            "name": "Color",
                            "value": "Blue",
                            "price_adjustment": 0,
                            "stock": 20,
                        },
                        {
                            "name": "Color",
                            "value": "Red",
                            "price_adjustment": 0,
                            "stock": 15,
                        },
                    ],
                },
            ],
            "Men's Clothing": [
                {
                    "name": "Premium Cotton T-Shirt",
                    "description": "Comfortable and stylish cotton t-shirt"
                    " for everyday wear.",
                    "price": Decimal("29.99"),
                    "variants": [
                        {
                            "name": "Size",
                            "value": "S",
                            "price_adjustment": 0,
                            "stock": 20,
                        },
                        {
                            "name": "Size",
                            "value": "M",
                            "price_adjustment": 0,
                            "stock": 35,
                        },
                        {
                            "name": "Size",
                            "value": "L",
                            "price_adjustment": 0,
                            "stock": 30,
                        },
                        {
                            "name": "Size",
                            "value": "XL",
                            "price_adjustment": 0,
                            "stock": 25,
                        },
                    ],
                },
                {
                    "name": "Slim Fit Jeans",
                    "description": "Modern slim fit jeans made from premium denim.",
                    "price": Decimal("89.99"),
                    "variants": [
                        {
                            "name": "Waist",
                            "value": "30",
                            "price_adjustment": 0,
                            "stock": 15,
                        },
                        {
                            "name": "Waist",
                            "value": "32",
                            "price_adjustment": 0,
                            "stock": 25,
                        },
                        {
                            "name": "Waist",
                            "value": "34",
                            "price_adjustment": 0,
                            "stock": 30,
                        },
                        {
                            "name": "Waist",
                            "value": "36",
                            "price_adjustment": 0,
                            "stock": 20,
                        },
                    ],
                },
            ],
            "Women's Clothing": [
                {
                    "name": "Floral Summer Dress",
                    "description": "Beautiful floral dress perfect for"
                    " summer occasions.",
                    "price": Decimal("79.99"),
                    "variants": [
                        {
                            "name": "Size",
                            "value": "XS",
                            "price_adjustment": 0,
                            "stock": 15,
                        },
                        {
                            "name": "Size",
                            "value": "S",
                            "price_adjustment": 0,
                            "stock": 25,
                        },
                        {
                            "name": "Size",
                            "value": "M",
                            "price_adjustment": 0,
                            "stock": 30,
                        },
                        {
                            "name": "Size",
                            "value": "L",
                            "price_adjustment": 0,
                            "stock": 20,
                        },
                    ],
                },
                {
                    "name": "Leather Jacket",
                    "description": "Classic leather jacket for a timeless look.",
                    "price": Decimal("199.99"),
                    "variants": [
                        {
                            "name": "Size",
                            "value": "S",
                            "price_adjustment": 0,
                            "stock": 12,
                        },
                        {
                            "name": "Size",
                            "value": "M",
                            "price_adjustment": 0,
                            "stock": 18,
                        },
                        {
                            "name": "Size",
                            "value": "L",
                            "price_adjustment": 0,
                            "stock": 15,
                        },
                    ],
                },
            ],
            "Furniture": [
                {
                    "name": "Modern Office Chair",
                    "description": "Ergonomic office chair with lumbar support.",
                    "price": Decimal("299.99"),
                    "variants": [
                        {
                            "name": "Color",
                            "value": "Black",
                            "price_adjustment": 0,
                            "stock": 20,
                        },
                        {
                            "name": "Color",
                            "value": "Gray",
                            "price_adjustment": 0,
                            "stock": 15,
                        },
                        {
                            "name": "Color",
                            "value": "White",
                            "price_adjustment": 0,
                            "stock": 10,
                        },
                    ],
                },
                {
                    "name": "Standing Desk",
                    "description": "Adjustable height standing desk for a"
                    " healthy workspace.",
                    "price": Decimal("599.99"),
                    "stock": 25,
                },
            ],
            "Fitness": [
                {
                    "name": "Adjustable Dumbbells",
                    "description": "Space-saving adjustable dumbbells for"
                    " home workouts.",
                    "price": Decimal("299.99"),
                    "variants": [
                        {
                            "name": "Weight",
                            "value": "5-25 lbs",
                            "price_adjustment": 0,
                            "stock": 15,
                        },
                        {
                            "name": "Weight",
                            "value": "5-50 lbs",
                            "price_adjustment": 200,
                            "stock": 10,
                        },
                    ],
                },
                {
                    "name": "Yoga Mat Premium",
                    "description": "Non-slip premium yoga mat for all fitness levels.",
                    "price": Decimal("49.99"),
                    "variants": [
                        {
                            "name": "Color",
                            "value": "Purple",
                            "price_adjustment": 0,
                            "stock": 25,
                        },
                        {
                            "name": "Color",
                            "value": "Blue",
                            "price_adjustment": 0,
                            "stock": 20,
                        },
                        {
                            "name": "Color",
                            "value": "Pink",
                            "price_adjustment": 0,
                            "stock": 15,
                        },
                    ],
                },
            ],
        }

        product_count = 0
        for category_name, products in products_data.items():
            if category_name not in categories:
                continue

            category = categories[category_name]

            for product_data in products:
                # Create product
                product = Product.objects.create(
                    name=product_data["name"],
                    slug=slugify(product_data["name"]),
                    description=product_data["description"],
                    category=category,
                    price=product_data["price"],
                    stock_quantity=product_data.get("stock", 100),
                    sku=f"SKU{1000 + product_count:04d}",
                    is_active=True,
                    is_featured=random.choice([True, False]),
                    meta_title=product_data["name"],
                    meta_description=product_data["description"][:150],
                )

                # Create variants if specified
                if "variants" in product_data:
                    for variant_data in product_data["variants"]:
                        ProductVariant.objects.create(
                            product=product,
                            name=variant_data["name"],
                            value=variant_data["value"],
                            price_adjustment=variant_data.get("price_adjustment", 0),
                            stock_quantity=variant_data["stock"],
                        )

                product_count += 1
                self.stdout.write(f"  Created product: {product.name}")

        self.stdout.write(f"Created {product_count} products total")

    def create_sample_users(self):
        """Create sample users with profiles"""
        self.stdout.write("Creating sample users...")

        users_data = [
            {
                "username": "john_doe",
                "email": "john@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "profile": {
                    "phone_number": "+1-555-0123",
                    "address_line_1": "123 Main St",
                    "city": "New York",
                    "state_province": "NY",
                    "postal_code": "10001",
                    "country": "US",
                },
            },
            {
                "username": "jane_smith",
                "email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "profile": {
                    "phone_number": "+1-555-0456",
                    "address_line_1": "456 Oak Ave",
                    "city": "Los Angeles",
                    "state_province": "CA",
                    "postal_code": "90210",
                    "country": "US",
                },
            },
            {
                "username": "mike_wilson",
                "email": "mike@example.com",
                "first_name": "Mike",
                "last_name": "Wilson",
                "profile": {
                    "phone_number": "+1-555-0789",
                    "address_line_1": "789 Pine St",
                    "city": "Chicago",
                    "state_province": "IL",
                    "postal_code": "60601",
                    "country": "US",
                },
            },
        ]

        for user_data in users_data:
            # Create user
            user = User.objects.create_user(
                username=user_data["username"],
                email=user_data["email"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                # In production, use proper password generation
                password="samplepass123",  # nosec B106
            )

            # Update profile (should be created automatically by signal)
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile_data = user_data["profile"]
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()

            self.stdout.write(f"  Created user: {user.username}")

        self.stdout.write("Sample data creation completed!")
        self.stdout.write("---")
        self.stdout.write("Sample user credentials (username/password):")
        for user_data in users_data:
            self.stdout.write(f'  {user_data["username"]}/samplepass123')
