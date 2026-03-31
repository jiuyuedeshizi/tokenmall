from app.services.observability import export_metrics_text, increment_metric, observe_metric


def test_export_metrics_text_contains_counters_and_timings():
    increment_metric("proxy.upstream_success_total")
    observe_metric("proxy.upstream_request", 0.25)

    payload = export_metrics_text()

    assert "proxy_upstream_success_total" in payload
    assert "proxy_upstream_request_seconds_count" in payload
    assert "proxy_upstream_request_seconds_sum" in payload
