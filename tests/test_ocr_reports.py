import os
import runpy


def test_find_pages_sorted(tmp_path):
    # create some page_* image files and other files
    (tmp_path / "page_2.png").write_text("")
    (tmp_path / "page_10.png").write_text("")
    (tmp_path / "page_1.png").write_text("")
    (tmp_path / "ignore.txt").write_text("")

    mod = runpy.run_path("scripts/ocr_reports.py")
    find_pages = mod["find_pages"]
    pages = find_pages(str(tmp_path))
    basenames = [os.path.basename(p) for p in pages]
    # script uses lexicographic sort
    assert basenames == ["page_1.png", "page_10.png", "page_2.png"]


def test_ocr_image_to_text_success(monkeypatch):
    mod = runpy.run_path("scripts/ocr_reports.py")

    captured = {}

    def fake_run(cmd, capture_output=True, check=True):
        # record the command and return a fake CompletedProcess-like object
        captured["cmd"] = cmd

        class R:
            stdout = b"hello world\n"

        return R()

    monkeypatch.setattr(mod["subprocess"], "run", fake_run)

    txt = mod["ocr_image_to_text"]("some.png", lang="chi_sim")
    assert "hello world" in txt
    # ensure -l lang was inserted into the command list
    assert "-l" in captured["cmd"] and "chi_sim" in captured["cmd"]


def test_ocr_image_to_text_callederr(monkeypatch):
    mod = runpy.run_path("scripts/ocr_reports.py")

    def fake_run(cmd, capture_output=True, check=True):
        raise mod["subprocess"].CalledProcessError(
            2, cmd, stderr=b"error from tesseract"
        )

    monkeypatch.setattr(mod["subprocess"], "run", fake_run)

    txt = mod["ocr_image_to_text"]("some.png")
    assert "[TESSERACT_ERROR" in txt
    assert "error from tesseract" in txt


def test_ocr_image_to_text_file_not_found(monkeypatch):
    mod = runpy.run_path("scripts/ocr_reports.py")

    def fake_run(cmd, capture_output=True, check=True):
        raise FileNotFoundError()

    monkeypatch.setattr(mod["subprocess"], "run", fake_run)

    try:
        mod["ocr_image_to_text"]("x.png")
        raise AssertionError("Expected RuntimeError when tesseract not found")
    except RuntimeError as e:
        assert "tesseract not found" in str(e)
