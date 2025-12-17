# views.py
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET
from scrap.models import Product
import socket
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from scrap.models import Product
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.conf import settings
from pathlib import Path
@require_GET
def get_product_batch(request):
    """
    ?limit=500
    """
    limit = int(request.GET.get("limit", 500))
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # Proxy arkasında ise ilk IP gerçek client IP'dir
        worker_id = x_forwarded_for.split(",")[0].strip()
    else:
        # Direkt bağlantı
        worker_id = request.META.get("REMOTE_ADDR")

    with transaction.atomic():
        qs = (
            Product.objects
            .select_for_update(skip_locked=True)
            .filter(status="pending")
            .order_by("id")[:limit]
        )

        products = list(qs)

        if not products:
            return JsonResponse({"status": "empty", "products": []})

        Product.objects.filter(
            id__in=[p.id for p in products]
        ).update(
            status="processing",
            locked_by=worker_id,
            locked_at=timezone.now()
        )
    print('products',products)
    return JsonResponse({
        "status": "ok",
        "count": len(products),
        "products": [
            {"id": p.id, "url": p.url}
            for p in products
        ]
    })


@csrf_exempt
def update_product(request):
    data = json.loads(request.body)

    product = Product.objects.get(id=data["id"])

    product.name = data.get("name")
    product.desc = data.get("desc")
    product.code = data.get("code")
    product.category_hierarchy = data.get("category_hierarchy")
    product.image_url = data.get("image_url")
    product.status = data.get("status", "done")

    product.save()

    return JsonResponse({"ok": True})

def reset_stuck_products(request):
    timeout = timezone.now() - timedelta(hours=2)

    qs = Product.objects.filter(
        status__in=["processing", "error"],
        # locked_at__lt=timeout
    )
    # qs = Product.objects.all()

    count = qs.update(
        status="pending",
        locked_by=None,
        locked_at=None
    )

    return JsonResponse({"reset_count": count})

def product_status(request):
    return JsonResponse({
        "pending": Product.objects.filter(status="pending").count(),
        "processing": Product.objects.filter(status="processing").count(),
        "done": Product.objects.filter(status="done").count(),
        "error": Product.objects.filter(status="error").count(),
        "processing_list": list(
            Product.objects.filter(status="processing")
            .values("id", "url", "locked_by", "locked_at")[:50]
        )
    })

def dashboard(request):
    return render(request, "dashboard.html")




def processed_products(request):
    page_number = request.GET.get("page", 1)

    qs = Product.objects.exclude(status="pending").exclude(status="processing").order_by("-id")
    total_count = qs.count()  # 🔹 pagination'dan bağımsız

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "processed_products.html",
        {
            "page_obj": page_obj,
            "total_count": total_count,
        }
    )

def download_sqlite(request):
    if not request.user.is_superuser:
        raise Http404()

    db_path = Path(settings.BASE_DIR) / "db.sqlite3"
    if not db_path.exists():
        raise Http404()

    return FileResponse(
        open(db_path, "rb"),
        as_attachment=True,
        filename="db.sqlite3"
    )



