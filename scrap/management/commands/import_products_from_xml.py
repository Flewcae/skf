import os
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand
from django.conf import settings

from scrap.models import Product


class Command(BaseCommand):
    help = "Sitemap XML dosyalarındaki URL'lerden Product oluşturur"

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        xml_dir = os.path.join(base_dir, "xml")

        if not os.path.exists(xml_dir):
            self.stdout.write(self.style.ERROR("xml klasörü bulunamadı"))
            return

        xml_files = [f for f in os.listdir(xml_dir) if f.endswith(".xml")]

        if not xml_files:
            self.stdout.write(self.style.WARNING("XML dosyası bulunamadı"))
            return

        created_count = 0

        # Sitemap namespace
        namespaces = {
            "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
        }

        for xml_file in xml_files:
            file_path = os.path.join(xml_dir, xml_file)
            self.stdout.write(f"İşleniyor: {xml_file}")

            tree = ET.parse(file_path)
            root = tree.getroot()

            for loc in root.findall("ns:url/ns:loc", namespaces):
                url = loc.text.strip()

                if not url:
                    continue

                _, created = Product.objects.get_or_create(
                    url=url
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"{created_count}. Product oluşturuldu")
                    )
        self.stdout.write(
            self.style.SUCCESS(f"Toplam {created_count} adet Product oluşturuldu")
        )
