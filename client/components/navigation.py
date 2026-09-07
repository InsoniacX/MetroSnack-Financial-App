import asyncio


def navigate(page, route):
    """Jadwalkan navigasi Flet tanpa memakai Page.go yang deprecated."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return page.run_task(page.push_route, route)

    return loop.create_task(page.push_route(route))
