# Spec: Shopping Cart Functionality

**Epic:** EPIC-03  
**Priority:** High  
**Component:** Cart (orders app)  
**Story Points:** 19  
**Dependencies:** EPIC-01 (Database Models), EPIC-02 (Product Catalog)  
**Status:** ✅ Complete

## Description

A comprehensive shopping cart system that allows customers to add products, manage
quantities, persist cart contents across sessions, and provides seamless integration
with the checkout process.

## User Story

As a customer, I want to add products to my shopping cart, modify quantities, and have
my cart persist across browser sessions so that I can easily manage my purchases and
proceed to checkout when ready.

## Acceptance Criteria

- [x] Add products to cart with AJAX functionality
- [x] Update and remove cart items with real-time total updates
- [x] Cart persistence for both anonymous and authenticated users
- [x] Cart summary display with taxes and shipping estimates
- [x] Inventory validation and out-of-stock handling
- [x] Cart migration when user logs in (anonymous → authenticated merge)

## Scope

### In Scope
- Session-based cart for anonymous users (Django sessions)
- Database-backed cart for authenticated users (Cart/CartItem models)
- AJAX add/update/remove cart operations
- Stock validation before adding to cart
- Cart context processor for navbar badge count
- Cart migration on login (merge session cart → user cart)
- Checkout flow (existing)
- Cart/order templates

### Out of Scope
- Payment processing
- Coupon/discount codes
- Wishlist / save-for-later  
- Cart abandonment emails
- "Frequently bought together" recommendations
