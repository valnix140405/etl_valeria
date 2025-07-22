import requests

def paginated_get(base_url, page_param="page", results_key="results", pagination_key="pagination", max_pages=None):
    """
    Realiza requests paginados a una API hasta agotar páginas o llegar al límite.
    Retorna lista unificada de todos los resultados.
    """
    results = []
    page = 1

    while True:
        url = f"{base_url}?{page_param}={page}"
        response = requests.get(url)
        data = response.json()

        if results_key not in data:
            break

        page_results = data[results_key]
        results.extend(page_results)

        if max_pages and page >= max_pages:
            break

        if pagination_key in data and page >= data[pagination_key].get("pages", 0):
            break

        page += 1

    return results 