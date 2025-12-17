from django.urls import path
from scrap import views

urlpatterns = [
    path(
        "api/get-product-batch/",
        views.get_product_batch,
        name="get_product_batch"
    ),

    path(
        "api/update-product/",
        views.update_product,
        name="update_product"
    ),

    path(
        "api/reset-stuck-products/",
        views.reset_stuck_products,
        name="reset_stuck_products"
    ),
    path(
        "api/product-status/",
        views.product_status,
        name="product_status"
    ),
    path(
        "",
        views.dashboard,
        name="dashboard"
    ),
    path(
        "products/",
        views.processed_products,
        name="processed_products"
    ),
    path("_internal/download-db/", views.download_sqlite),


]
