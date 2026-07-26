"""Connect to Asterisk ARI WebSocket and ingest call events into CRM."""

from __future__ import annotations

import asyncio

from django.core.management.base import BaseCommand, CommandError

from crm.ari_bridge import list_asterisk_connectors, run_bridges


class Command(BaseCommand):
    help = (
        "Live Asterisk ARI WebSocket bridge: subscribe to /ari/events and "
        "create telephony Activities for active asterisk connectors."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--connector-id",
            type=int,
            default=None,
            help="Only bridge this IntegrationConnector id",
        )
        parser.add_argument(
            "--reconnect-delay",
            type=float,
            default=5.0,
            help="Seconds to wait before reconnect (default 5)",
        )
        parser.add_argument(
            "--max-messages",
            type=int,
            default=None,
            help="Stop after N messages (for tests/smoke)",
        )

    def handle(self, *args, **options):
        connectors = list_asterisk_connectors(connector_id=options["connector_id"])
        if not connectors:
            raise CommandError(
                "No active telephony connectors with pbx=asterisk and ari_base_url"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting ARI bridge for {len(connectors)} connector(s): "
                + ", ".join(str(c.id) for c in connectors)
            )
        )
        try:
            asyncio.run(
                run_bridges(
                    connectors,
                    reconnect_delay=options["reconnect_delay"],
                    max_messages=options["max_messages"],
                )
            )
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("ARI bridge stopped"))
