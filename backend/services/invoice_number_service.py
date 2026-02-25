"""
Invoice Number Generation Service
Supports configurable formats with multiple segment types.
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional
from database import db
from fastapi import HTTPException


class InvoiceNumberService:
    """Generate invoice numbers based on configurable format."""

    @staticmethod
    async def generate_invoice_number(tenant_id: str, trip_id: Optional[str] = None) -> str:
        """
        Generate invoice number based on tenant's configuration.

        Segment types:
        - STATIC: Fixed text (e.g., "INV", "S")
        - YEAR: Current year (2-digit or 4-digit)
        - MONTH: Current month (1-digit or 2-digit zero-padded)
        - TRIP_SEQ: Per-trip counter (requires trip_id)
        - GLOBAL_SEQ: Global counter across all invoices

        Example format: S-{YEAR:2}-{MONTH:2}-{GLOBAL_SEQ:3} -> S-26-02-001
        """
        settings = await db.settings.find_one({"tenant_id": tenant_id})

        if not settings or not settings.get("invoice_number_format"):
            segments = [
                {"type": "STATIC", "value": "INV"},
                {"type": "YEAR", "digits": 4},
                {"type": "GLOBAL_SEQ", "digits": 3}
            ]
            separator = "-"
        else:
            format_config = settings["invoice_number_format"]
            segments = format_config.get("segments", [])
            separator = format_config.get("separator", "-")

        parts = []
        now = datetime.now(timezone.utc)
        year = now.year
        month = now.month

        for segment in segments:
            seg_type = segment["type"]

            if seg_type == "STATIC":
                parts.append(segment["value"])

            elif seg_type == "YEAR":
                digits = segment.get("digits", 4)
                if digits == 2:
                    parts.append(str(year)[-2:])
                else:
                    parts.append(str(year))

            elif seg_type == "MONTH":
                digits = segment.get("digits", 2)
                parts.append(str(month).zfill(digits))

            elif seg_type == "TRIP_SEQ":
                if not trip_id:
                    raise HTTPException(400, "trip_id required for TRIP_SEQ format")

                trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id})
                if not trip:
                    raise HTTPException(404, "Trip not found")

                current_seq = trip.get("invoice_seq", 0)
                next_seq = current_seq + 1

                await db.trips.update_one(
                    {"id": trip_id, "tenant_id": tenant_id},
                    {"$set": {"invoice_seq": next_seq}}
                )

                digits = segment.get("digits", 3)
                parts.append(str(next_seq).zfill(digits))

            elif seg_type == "GLOBAL_SEQ":
                counter_key = f"invoice_seq_{tenant_id}"

                counter_doc = await db.counters.find_one_and_update(
                    {"key": counter_key},
                    {"$inc": {"value": 1}},
                    upsert=True,
                    return_document=True
                )

                digits = segment.get("digits", 3)
                parts.append(str(counter_doc["value"]).zfill(digits))

        return separator.join(parts)

    @staticmethod
    async def preview_format(segments: List[Dict], separator: str = "-") -> str:
        """Generate a preview of what the invoice number format will look like."""
        parts = []
        now = datetime.now(timezone.utc)
        year = now.year
        month = now.month

        for segment in segments:
            seg_type = segment["type"]

            if seg_type == "STATIC":
                parts.append(segment.get("value", "TEXT"))
            elif seg_type == "YEAR":
                digits = segment.get("digits", 4)
                parts.append(str(year)[-digits:] if digits == 2 else str(year))
            elif seg_type == "MONTH":
                digits = segment.get("digits", 2)
                parts.append(str(month).zfill(digits))
            elif seg_type in ["TRIP_SEQ", "GLOBAL_SEQ"]:
                digits = segment.get("digits", 3)
                parts.append("X" * digits)

        return separator.join(parts)
