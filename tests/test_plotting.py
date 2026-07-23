import inspect

from dynamic_ac_generator import plotting


def test_static_load_impedance_figure_uses_stacked_shared_time_axes() -> None:
    source = inspect.getsource(plotting.generate_all_figures)

    assert "plt.subplots(" in source
    assert "2," in source
    assert "1," in source
    assert "sharex=True" in source
    assert "impedance_magnitude_axis" in source
    assert "impedance_angle_axis" in source
    assert ".twinx()" not in source
    assert '"Load Impedance Magnitude Versus Time"' in source
    assert '"Load Impedance Angle Versus Time"' in source
