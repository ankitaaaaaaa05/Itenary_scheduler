"""
geocoder.py — Free geocoding via Nominatim (OpenStreetMap)
No API key required. Rate limit: 1 req/sec.
"""
import requests
import requests.packages.urllib3
import time
import streamlit as st

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "AITravelLogisticsPlanner/1.0"}


def geocode(address: str) -> dict | None:
    """
    Convert a place name / address string to {lat, lng, display_name}.
    Returns None if not found or on error.
    """
    if not address or not address.strip():
        return None
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={
                "q": address.strip(),
                "format": "json",
                "limit": 5,
                "addressdetails": 1,
            },
            headers=HEADERS,
            timeout=8,
            verify=False,   # disable SSL cert verification (corporate proxy / self-signed cert)
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            top = results[0]
            return {
                "lat": float(top["lat"]),
                "lng": float(top["lon"]),
                "display_name": top.get("display_name", address),
                "all_results": [
                    {
                        "display_name": r.get("display_name", ""),
                        "lat": float(r["lat"]),
                        "lng": float(r["lon"]),
                    }
                    for r in results
                ],
            }
    except Exception as e:
        st.warning(f"Geocoding error for '{address}': {e}")
    return None


def geocode_cached(address: str) -> dict | None:
    """Cached wrapper to avoid redundant API calls within a session."""
    cache_key = f"geo_{address.strip().lower()}"
    if cache_key not in st.session_state:
        time.sleep(0.2)  # Nominatim polite delay
        st.session_state[cache_key] = geocode(address)
    return st.session_state[cache_key]


def render_location_picker(label: str, key_prefix: str, default_address: str = "") -> dict:
    """
    Renders a location search widget outside a form.
    Returns dict with {name, lat, lng}.
    Stores resolved coords in session state under key_prefix.
    """
    addr_key = f"{key_prefix}_addr"
    lat_key = f"{key_prefix}_lat"
    lng_key = f"{key_prefix}_lng"
    name_key = f"{key_prefix}_name"

    # Init session state
    if addr_key not in st.session_state:
        st.session_state[addr_key] = default_address
    if lat_key not in st.session_state:
        st.session_state[lat_key] = 0.0
    if lng_key not in st.session_state:
        st.session_state[lng_key] = 0.0
    if name_key not in st.session_state:
        st.session_state[name_key] = default_address

    st.markdown(f"**{label}**")
    col_input, col_btn = st.columns([4, 1])

    with col_input:
        address_input = st.text_input(
            "Search address or place name",
            value=st.session_state[addr_key],
            key=f"{key_prefix}_input",
            placeholder="e.g. Gateway of India, Mumbai",
            label_visibility="collapsed",
        )

    with col_btn:
        search_clicked = st.button("🔍 Search", key=f"{key_prefix}_search", use_container_width=True)

    if search_clicked and address_input.strip():
        with st.spinner(f"Searching '{address_input}'..."):
            result = geocode(address_input)
        if result:
            # If multiple results, show a selectbox
            if len(result["all_results"]) > 1:
                options = [r["display_name"] for r in result["all_results"]]
                choice_key = f"{key_prefix}_choice"
                chosen = st.selectbox(
                    "Multiple results found — select one:",
                    options,
                    key=choice_key,
                )
                chosen_idx = options.index(chosen)
                chosen_data = result["all_results"][chosen_idx]
                st.session_state[lat_key] = chosen_data["lat"]
                st.session_state[lng_key] = chosen_data["lng"]
                st.session_state[name_key] = chosen_data["display_name"]
            else:
                st.session_state[lat_key] = result["lat"]
                st.session_state[lng_key] = result["lng"]
                st.session_state[name_key] = result["display_name"]

            st.session_state[addr_key] = address_input
            st.rerun()
        else:
            st.error(f"No results found for '{address_input}'. Try a more specific address.")

    # Show resolved coordinates
    if st.session_state[lat_key] != 0.0:
        st.success(
            f"📍 **{st.session_state[name_key][:80]}**  "
            f"| Lat: `{st.session_state[lat_key]:.5f}` "
            f"| Lng: `{st.session_state[lng_key]:.5f}`"
        )
    else:
        st.caption("⚠️ No location resolved yet — click Search.")

    return {
        "name": st.session_state[name_key] or address_input,
        "lat": st.session_state[lat_key],
        "lng": st.session_state[lng_key],
    }