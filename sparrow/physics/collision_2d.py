from sparrow.types import Rectangle


def check_collision_rects(a: Rectangle, b: Rectangle) -> bool:
    if (
        a.x < (b.x + b.width)
        and (a.x + a.width) > b.x
        and a.y < (b.y + b.height)
        and (a.y + a.height) > b.y
    ):
        return True

    return False


def get_collision_rect(a: Rectangle, b: Rectangle) -> Rectangle:
    raise NotImplementedError
