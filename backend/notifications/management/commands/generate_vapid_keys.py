from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate VAPID key pair for Web Push (print env lines)."

    def handle(self, *args, **options):
        import base64

        from cryptography.hazmat.primitives import serialization
        from py_vapid import Vapid

        vapid = Vapid()
        vapid.generate_keys()
        raw_pub = vapid.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        public_key = base64.urlsafe_b64encode(raw_pub).decode().rstrip("=")
        raw_priv = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
        private_key = base64.urlsafe_b64encode(raw_priv).decode().rstrip("=")

        self.stdout.write("Add to .env:\n")
        self.stdout.write(f"VAPID_PUBLIC_KEY={public_key}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private_key}")
        self.stdout.write("VAPID_SUBJECT=mailto:admin@example.com")
