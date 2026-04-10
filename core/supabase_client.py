"""
Cliente Supabase singleton. Usar service_role key no backend
(bypassa RLS — seguro porque o código valida agency_id manualmente).
"""
import os
from supabase import create_client, Client

_client: Client | None = None

def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.environ.get("SUPABASE_URL", ""),
            os.environ.get("SUPABASE_SERVICE_KEY", ""),  # service_role bypassa RLS
        )
    return _client
