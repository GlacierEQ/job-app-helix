from job_app_helix.privacy_boundary import assert_public_projection_safe, scan_public_projection


def test_capability_evidence_allowed():
    text = "Built an agent runtime with provider readback and evidence-bound claims."
    assert scan_public_projection(text) == []
    assert_public_projection_safe(text)


def test_application_operations_rejected():
    findings = scan_public_projection("Application status: under review.")
    assert findings
    try:
        assert_public_projection_safe("Application status: under review.")
    except ValueError:
        pass
    else:
        raise AssertionError("private application operation was accepted")
