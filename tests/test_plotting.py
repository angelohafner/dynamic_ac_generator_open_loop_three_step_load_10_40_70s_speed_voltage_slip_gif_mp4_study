import inspect

from dynamic_ac_generator import plotting


def test_static_load_figure_uses_stacked_shared_time_axes_and_admittance_outputs() -> None:
    source = inspect.getsource(plotting.generate_all_figures)

    assert "plt.subplots(" in source
    assert "2," in source
    assert "1," in source
    assert "sharex=True" in source
    assert "impedance_magnitude_axis" in source
    assert "impedance_angle_axis" in source
    assert ".twinx()" not in source
    assert "results.load_impedance_real_ohm" in source
    assert "results.load_impedance_imag_ohm" in source
    assert "results.load_admittance_real_pu" in source
    assert "results.load_admittance_imag_pu" in source
    assert "results.load_admittance_magnitude_pu" in source
    assert "results.load_admittance_angle_deg" in source
    assert '"G"' in source
    assert '"B"' in source
    assert '"|Y|"' in source
    assert '"Re(Z)"' in source
    assert '"Im(Z)"' in source
    assert '"Load Admittance Versus Time"' in source
    assert '"Load Admittance Angle Versus Time"' in source
