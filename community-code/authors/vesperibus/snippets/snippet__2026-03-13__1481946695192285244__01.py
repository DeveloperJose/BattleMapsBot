def get_dot_color(c):
    if c > 0:
        return dark_green
    elif c < 0:
        return red_color
    else:
        return blue_color

colors = [get_dot_color(c) for c in df['change']]
