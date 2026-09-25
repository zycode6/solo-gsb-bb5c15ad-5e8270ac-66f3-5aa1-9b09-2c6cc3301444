"""骑马订爬移补偿（creep-plan）算法单元测试。"""
import pytest

from app.imposition import creep_plan


def _by_slot(result, signature_index, sheet_index, side):
    """取指定帖/张/面的左右槽位移记录。"""
    slots = {
        item["slot"]: item
        for item in result["placements"]
        if item["signature_index"] == signature_index
        and item["sheet_index"] == sheet_index
        and item["side"] == side
    }
    return slots["left"], slots["right"]


def test_outermost_sheet_has_zero_creep():
    # 4 页 1 张：最外张爬移量为 0，四个页位位移全为 0
    result = creep_plan(4, 1, "left", 210.0, 297.0, 0.0, "long", 0.1)
    assert result["signature_count"] == 1
    assert result["thickness_mm"] == 0.1
    assert result["paper_width_mm"] == 420.0
    for item in result["placements"]:
        assert item["paper_shift_x_mm"] == 0.0
        assert item["artwork_shift_x_mm"] == 0.0


def test_paper_shift_points_toward_fold_center_long():
    # 8 页 2 张、long 背面交换槽位：
    # 正面 (8,1)/(6,3)，long 背面槽位：左=7 右=2（张1）、左=5 右=4（张2）
    result = creep_plan(8, 2, "left", 100.0, 200.0, 0.0, "long", 0.1)
    # 张 1（最外张）位移 0
    fl1, fr1 = _by_slot(result, 1, 1, "front")
    assert (fl1["page"], fl1["paper_shift_x_mm"]) == (8, 0.0)
    assert (fr1["page"], fr1["paper_shift_x_mm"]) == (1, 0.0)
    # 张 2（向内第 2 张）爬移量 2×1×0.1 = 0.2：左槽 +0.2、右槽 -0.2
    fl2, fr2 = _by_slot(result, 1, 2, "front")
    assert fl2["page"] == 6
    assert fl2["paper_shift_x_mm"] == pytest.approx(0.2)
    assert fl2["artwork_shift_x_mm"] == pytest.approx(0.2)
    assert fr2["page"] == 3
    assert fr2["paper_shift_x_mm"] == pytest.approx(-0.2)
    assert fr2["artwork_shift_x_mm"] == pytest.approx(-0.2)
    # long 背面槽位交换，旋转 0°，阅读位移与纸面位移同号
    bl2, br2 = _by_slot(result, 1, 2, "back")
    assert bl2["page"] == 5
    assert bl2["paper_shift_x_mm"] == pytest.approx(0.2)
    assert br2["page"] == 4
    assert br2["paper_shift_x_mm"] == pytest.approx(-0.2)


def test_short_flip_back_180_artwork_shift_reverses_sign():
    # 8 页 2 张、short 背面：槽位保持（背左=2、背右=7 等），旋转 180°
    result = creep_plan(8, 2, "left", 100.0, 200.0, 0.0, "short", 0.25)
    # 张 2 爬移量 = 2×1×0.25 = 0.5
    bl2, br2 = _by_slot(result, 1, 2, "back")
    assert bl2["page"] == 4
    # 左槽纸面位移 +0.5；180° 旋转后阅读方向位移为 -0.5
    assert bl2["paper_shift_x_mm"] == pytest.approx(0.5)
    assert bl2["artwork_shift_x_mm"] == pytest.approx(-0.5)
    assert br2["page"] == 5
    assert br2["paper_shift_x_mm"] == pytest.approx(-0.5)
    assert br2["artwork_shift_x_mm"] == pytest.approx(0.5)
    # 正面旋转 0°，位移同号
    fl2, fr2 = _by_slot(result, 1, 2, "front")
    assert fl2["paper_shift_x_mm"] == pytest.approx(0.5)
    assert fl2["artwork_shift_x_mm"] == pytest.approx(0.5)
    assert fr2["artwork_shift_x_mm"] == pytest.approx(-0.5)


def test_creep_independent_per_signature():
    # 10 页、每帖 2 张（容量 8 页）-> 帖1 装满 2 张，帖2 2 页补白后 1 张；
    # 帖 2 只有 1 张，爬移量必须为 0（每帖独立从最外张起算）
    result = creep_plan(10, 2, "left", 100.0, 200.0, 0.0, "long", 0.1)
    assert result["signature_count"] == 2
    sig2 = [
        item for item in result["placements"]
        if item["signature_index"] == 2
    ]
    assert {item["sheet_index"] for item in sig2} == {1}
    assert all(item["paper_shift_x_mm"] == 0.0 for item in sig2)
    # 帖 1 张 2 仍有 0.2 的爬移
    sig1_sheet2 = [
        item for item in result["placements"]
        if item["signature_index"] == 1 and item["sheet_index"] == 2
    ]
    assert all(item["paper_shift_x_mm"] != 0.0 for item in sig1_sheet2)


def test_blank_slots_preserved_with_zero_shift():
    # 1 页补 3 空白：正面 (null,1)、背面 (null,null)
    result = creep_plan(1, 1, "left", 210.0, 297.0, 0.0, "short", 0.1)
    fl, fr = _by_slot(result, 1, 1, "front")
    assert fl["page"] is None
    assert fl["paper_shift_x_mm"] == 0.0
    assert fl["artwork_shift_x_mm"] == 0.0
    assert fr["page"] == 1
    bl, br = _by_slot(result, 1, 1, "back")
    assert bl["page"] is None and br["page"] is None
    assert bl["paper_shift_x_mm"] == 0.0
    assert br["artwork_shift_x_mm"] == 0.0
    # 空白页位在内张同样保留且位移为 0（末帖补白可能落在内张）
    result = creep_plan(5, 2, "left", 100.0, 200.0, 0.0, "long", 0.1)
    inner_blanks = [
        item for item in result["placements"]
        if item["signature_index"] == 1 and item["sheet_index"] == 2
        and item["page"] is None
    ]
    assert inner_blanks  # 5..8 中 6..8 为空白，内张含空白页位
    assert all(item["paper_shift_x_mm"] == 0.0 for item in inner_blanks)
    assert all(item["artwork_shift_x_mm"] == 0.0 for item in inner_blanks)


def test_right_binding_uses_actual_slots():
    # 右装订镜像：正面 (1,4)，爬移只看实际槽位——左槽(第1页)向中缝为 +
    result = creep_plan(4, 1, "left", 100.0, 200.0, 10.0, "long", 0.1)
    result_right = creep_plan(4, 1, "right", 100.0, 200.0, 10.0, "long", 0.1)
    fl_l, fr_l = _by_slot(result, 1, 1, "front")
    fl_r, fr_r = _by_slot(result_right, 1, 1, "front")
    assert (fl_l["page"], fr_l["page"]) == (4, 1)
    assert (fl_r["page"], fr_r["page"]) == (1, 4)
    # 页码镜像，但同槽位（左/右）的纸面位移方向一致
    assert fl_l["paper_shift_x_mm"] == fl_r["paper_shift_x_mm"] == 0.0
    assert fr_l["paper_shift_x_mm"] == fr_r["paper_shift_x_mm"] == 0.0


def test_gutter_does_not_change_shift_amount():
    # 中缝只影响纸面宽与槽位 x，不影响爬移量
    result = creep_plan(8, 2, "left", 100.0, 200.0, 8.0, "long", 0.1)
    assert result["paper_width_mm"] == 208.0
    fl2, fr2 = _by_slot(result, 1, 2, "front")
    assert fl2["paper_shift_x_mm"] == pytest.approx(0.2)
    assert fr2["paper_shift_x_mm"] == pytest.approx(-0.2)


def test_creep_equal_to_page_width_returns_422():
    # 张 2 爬移量 = 2×1×50 = 100，恰好达到页宽 100 -> ValueError
    with pytest.raises(ValueError):
        creep_plan(8, 2, "left", 100.0, 200.0, 0.0, "long", 50.0)


def test_creep_exceeding_page_width_returns_422():
    with pytest.raises(ValueError):
        creep_plan(8, 2, "left", 100.0, 200.0, 0.0, "long", 60.0)


def test_creep_just_below_page_width_ok():
    # 张 2 爬移量 99.999 < 100，正常返回
    result = creep_plan(8, 2, "left", 100.0, 200.0, 0.0, "long", 49.9995)
    fl2, _ = _by_slot(result, 1, 2, "front")
    assert fl2["paper_shift_x_mm"] == pytest.approx(99.999)


def test_creep_error_reports_signature_and_sheet():
    # 每帖 2 张：帖 1 张 2 即达到页宽，错误信息指出帖 1 张 2
    with pytest.raises(ValueError, match="第 1 帖第 2 张"):
        creep_plan(16, 2, "left", 100.0, 200.0, 0.0, "long", 50.0)
    # 厚度较小使首帖不超限；多帖场景下后续帖同样逐张判定，
    # 末帖（仅 1 张，爬移 0）不影响首帖校验
    with pytest.raises(ValueError, match="第 1 帖第 2 张"):
        creep_plan(10, 2, "left", 100.0, 200.0, 0.0, "long", 50.0)


def test_invalid_thickness():
    for thickness in (0, -0.1, float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            creep_plan(4, 1, "left", 100.0, 200.0, 0.0, "long", thickness)


def test_layout_validation_reused():
    # 尺寸/装订方向等校验在 API（Pydantic）层；领域层沿用 press_layout 的
    # duplex_flip 校验
    with pytest.raises(ValueError):
        creep_plan(4, 1, "left", 100.0, 200.0, 0.0, "side", 0.1)
