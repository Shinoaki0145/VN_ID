"""Test script for VN_ID CCCD pipeline on real images with latency breakdown."""
import json
import os
from vn_id import CCCDPipeline


def print_timings(timings: dict[str, float]):
    """Pretty prints step-by-step latency and total elapsed time."""
    print("  [Latency Breakdown]")
    for step, ms in timings.items():
        if step != "total_ms":
            print(f"    - {step:<18}: {ms:8.2f} ms")
    total = timings.get("total_ms", sum(v for k, v in timings.items() if k != "total_ms"))
    print(f"    ------------------------------------")
    print(f"    * TỔNG THỜI GIAN    : {total:8.2f} ms ({total/1000.0:.2f}s)")


def main():
    print("=" * 64)
    print("  VN_ID PIPELINE - TEST DỮ LIỆU THỰC TẾ (REAL OCR & QR)")
    print("=" * 64)

    os.makedirs("output", exist_ok=True)

    # 1. Khởi tạo pipeline (Mặc định mock_mode=False -> dùng mô hình thật)
    pipeline = CCCDPipeline(device="auto", mock_mode=False)

    # 2. Test với cặp ảnh front_cu_2.png (ảnh mờ, không QR -> chạy 100% OCR) và back_cu_2.png
    front_path_2 = "image/front_cu_2.png"
    back_path_2 = "image/back_cu_2.png"

    if os.path.exists(front_path_2) and os.path.exists(back_path_2):
        print("\n[1] Kiểm thử cặp ảnh front_cu_2.png & back_cu_2.png:")
        res = pipeline.process_both_sides(front_path_2, back_path_2)
        d = res.data
        v = res.validation

        print(f"  + Số CCCD:              {d.id} (Nguồn: {res.field_sources.get('id')})")
        print(f"  + Họ và tên:            {d.name} (Nguồn: {res.field_sources.get('name')})")
        print(f"  + Ngày sinh:            {d.dob} (Nguồn: {res.field_sources.get('dob')})")
        print(f"  + Giới tính:            {d.gender} (Nguồn: {res.field_sources.get('gender')})")
        print(f"  + Quốc tịch:            {d.nationality} (Nguồn: {res.field_sources.get('nationality')})")
        print(f"  + Quê quán / Nơi ĐKKS:  {d.origin} (Nguồn: {res.field_sources.get('origin')})")
        print(f"  + Nơi thường trú / Cư trú: {d.residence} (Nguồn: {res.field_sources.get('residence')})")
        print(f"  + Ngày cấp (Mặt sau):   {d.issue_date} (Nguồn: {res.field_sources.get('issue_date')})")
        print(f"  + Có giá trị đến:       {d.expiry_date} (Nguồn: {res.field_sources.get('expiry_date')})")
        print(f"  + Nơi cấp (Mặt sau):    {d.issue_loc} (Nguồn: {res.field_sources.get('issue_loc')})")
        print(f"  + Hợp lệ 12 số:         {v.is_valid_12_digits} (Tỉnh: {v.province_valid}, Năm sinh: {v.birth_year_valid})")
        print_timings(res.timings)

        # Lưu kết quả
        with open("output/output_result.json", "w", encoding="utf-8") as f:
            json.dump(res.model_dump(), f, ensure_ascii=False, indent=2)
        print("  -> Đã lưu kết quả thực tế vào output/output_result.json")

    # 3. Test với ảnh front_cu.jpg (ảnh có mã QR thật)
    front_qr_path = "image/front_cu.jpg"
    if os.path.exists(front_qr_path):
        print(f"\n[2] Kiểm thử ảnh có QR code thật ({front_qr_path}):")
        res_qr = pipeline.process(front_qr_path)
        d_qr = res_qr.data
        print(f"  + Số CCCD:              {d_qr.id} (Nguồn: {res_qr.field_sources.get('id')})")
        print(f"  + Họ và tên:            {d_qr.name} (Nguồn: {res_qr.field_sources.get('name')})")
        print(f"  + Ngày sinh:            {d_qr.dob} (Nguồn: {res_qr.field_sources.get('dob')})")
        print(f"  + Giới tính:            {d_qr.gender} (Nguồn: {res_qr.field_sources.get('gender')})")
        print(f"  + Quê quán / Nơi ĐKKS:  {d_qr.origin} (Nguồn: {res_qr.field_sources.get('origin')})")
        print(f"  + Địa chỉ:              {d_qr.residence} (Nguồn: {res_qr.field_sources.get('residence')})")
        print(f"  + Có giá trị đến:       {d_qr.expiry_date} (Nguồn: {res_qr.field_sources.get('expiry_date')})")
        print_timings(res_qr.timings)

    # 4. Test với ảnh front_cu_10.jpg (ảnh QR mờ/hỏng, thuần OCR + Rule-based Parser fallback)
    front_10_path = "image/front_cu_10.jpg"
    if os.path.exists(front_10_path):
        print(f"\n[3] Kiểm thử ảnh QR hỏng / mờ, thuần OCR + Rule-based Parser fallback ({front_10_path}):")
        res_10 = pipeline.process(front_10_path)
        d_10 = res_10.data
        v_10 = res_10.validation
        print(f"  + Số CCCD:              {d_10.id} (Nguồn: {res_10.field_sources.get('id')})")
        print(f"  + Họ và tên:            {d_10.name} (Nguồn: {res_10.field_sources.get('name')})")
        print(f"  + Ngày sinh:            {d_10.dob} (Nguồn: {res_10.field_sources.get('dob')})")
        print(f"  + Giới tính:            {d_10.gender} (Nguồn: {res_10.field_sources.get('gender')})")
        print(f"  + Quốc tịch:            {d_10.nationality} (Nguồn: {res_10.field_sources.get('nationality')})")
        print(f"  + Quê quán:             {d_10.origin} (Nguồn: {res_10.field_sources.get('origin')})")
        print(f"  + Nơi thường trú:       {d_10.residence} (Nguồn: {res_10.field_sources.get('residence')})")
        print(f"  + Có giá trị đến:       {d_10.expiry_date} (Nguồn: {res_10.field_sources.get('expiry_date')})")
        print(f"  + Hợp lệ 12 số:         {v_10.is_valid_12_digits} (Tỉnh: {v_10.province_valid}, Năm sinh: {v_10.birth_year_valid})")
        print_timings(res_10.timings)

        with open("output/output_result_front_10.json", "w", encoding="utf-8") as f:
            json.dump(res_10.model_dump(), f, ensure_ascii=False, indent=2)
        print("  -> Đã lưu kết quả front_cu_10.jpg vào output/output_result_front_10.json")

    # 5. Test với Thẻ Căn cước mới 2024 (front_moi.jpg & back_moi.jpg - QR, Nơi cư trú, Nơi ĐKKS ở mặt sau)
    front_moi = "image/front_moi.jpg"
    back_moi = "image/back_moi.jpg"
    if os.path.exists(front_moi) and os.path.exists(back_moi):
        print(f"\n[4] Kiểm thử Thẻ Căn cước mới 2024 ({front_moi} & {back_moi}):")
        res_moi = pipeline.process_both_sides(front_moi, back_moi)
        d_m = res_moi.data
        v_m = res_moi.validation
        print(f"  + Số Căn cước:          {d_m.id} (Nguồn: {res_moi.field_sources.get('id')})")
        print(f"  + Số CMND cũ (từ QR):   {d_m.cmnd_old} (Nguồn: {res_moi.field_sources.get('cmnd_old')})")
        print(f"  + Họ và tên:            {d_m.name} (Nguồn: {res_moi.field_sources.get('name')})")
        print(f"  + Ngày sinh:            {d_m.dob} (Nguồn: {res_moi.field_sources.get('dob')})")
        print(f"  + Giới tính:            {d_m.gender} (Nguồn: {res_moi.field_sources.get('gender')})")
        print(f"  + Quốc tịch:            {d_m.nationality} (Nguồn: {res_moi.field_sources.get('nationality')})")
        print(f"  + Nơi ĐKKS (Mặt sau):   {d_m.origin} (Nguồn: {res_moi.field_sources.get('origin')})")
        print(f"  + Nơi cư trú (Mặt sau): {d_m.residence} (Nguồn: {res_moi.field_sources.get('residence')})")
        print(f"  + Ngày cấp (Mặt sau):   {d_m.issue_date} (Nguồn: {res_moi.field_sources.get('issue_date')})")
        print(f"  + Có giá trị đến:       {d_m.expiry_date} (Nguồn: {res_moi.field_sources.get('expiry_date')})")
        print(f"  + Nơi cấp (Mặt sau):    {d_m.issue_loc} (Nguồn: {res_moi.field_sources.get('issue_loc')})")
        if d_m.father_name:
            print(f"  + Họ tên Cha (từ QR):   {d_m.father_name} (Nguồn: {res_moi.field_sources.get('father_name')})")
        if d_m.mother_name:
            print(f"  + Họ tên Mẹ (từ QR):    {d_m.mother_name} (Nguồn: {res_moi.field_sources.get('mother_name')})")
        print(f"  + Hợp lệ 12 số:         {v_m.is_valid_12_digits} (Tỉnh: {v_m.province_valid}, Năm sinh: {v_m.birth_year_valid})")
        print_timings(res_moi.timings)

        # Lưu kết quả thẻ mới vào output/output_result_moi.json
        with open("output/output_result_moi.json", "w", encoding="utf-8") as f:
            json.dump(res_moi.model_dump(), f, ensure_ascii=False, indent=2)
        print("  -> Đã lưu kết quả Thẻ Căn cước mới vào output/output_result_moi.json")

    # 6. Test với Thẻ Căn cước mới 2024 mẫu 2 (front_moi_2.jpg & back_moi_2.jpg)
    front_moi_2 = "image/front_moi_2.jpg"
    back_moi_2 = "image/back_moi_2.jpg"
    if os.path.exists(front_moi_2) and os.path.exists(back_moi_2):
        print(f"\n[5] Kiểm thử Thẻ Căn cước mới 2024 mẫu 2 ({front_moi_2} & {back_moi_2}):")
        res_moi_2 = pipeline.process_both_sides(front_moi_2, back_moi_2)
        d_m2 = res_moi_2.data
        v_m2 = res_moi_2.validation
        print(f"  + Số Căn cước:          {d_m2.id} (Nguồn: {res_moi_2.field_sources.get('id')})")
        print(f"  + Họ và tên:            {d_m2.name} (Nguồn: {res_moi_2.field_sources.get('name')})")
        print(f"  + Ngày sinh:            {d_m2.dob} (Nguồn: {res_moi_2.field_sources.get('dob')})")
        print(f"  + Giới tính:            {d_m2.gender} (Nguồn: {res_moi_2.field_sources.get('gender')})")
        print(f"  + Quốc tịch:            {d_m2.nationality} (Nguồn: {res_moi_2.field_sources.get('nationality')})")
        print(f"  + Nơi ĐKKS (Mặt sau):   {d_m2.origin} (Nguồn: {res_moi_2.field_sources.get('origin')})")
        print(f"  + Nơi cư trú (Mặt sau): {d_m2.residence} (Nguồn: {res_moi_2.field_sources.get('residence')})")
        print(f"  + Ngày cấp (Mặt sau):   {d_m2.issue_date} (Nguồn: {res_moi_2.field_sources.get('issue_date')})")
        print(f"  + Có giá trị đến:       {d_m2.expiry_date} (Nguồn: {res_moi_2.field_sources.get('expiry_date')})")
        print(f"  + Nơi cấp (Mặt sau):    {d_m2.issue_loc} (Nguồn: {res_moi_2.field_sources.get('issue_loc')})")
        if d_m2.father_name:
            print(f"  + Họ tên Cha (từ QR):   {d_m2.father_name} (Nguồn: {res_moi_2.field_sources.get('father_name')})")
        if d_m2.mother_name:
            print(f"  + Họ tên Mẹ (từ QR):    {d_m2.mother_name} (Nguồn: {res_moi_2.field_sources.get('mother_name')})")
        print(f"  + Hợp lệ 12 số:         {v_m2.is_valid_12_digits} (Tỉnh: {v_m2.province_valid}, Năm sinh: {v_m2.birth_year_valid})")
        print_timings(res_moi_2.timings)

        # Lưu kết quả thẻ mới mẫu 2 vào output/output_result_moi_2.json
        with open("output/output_result_moi_2.json", "w", encoding="utf-8") as f:
            json.dump(res_moi_2.model_dump(), f, ensure_ascii=False, indent=2)
        print("  -> Đã lưu kết quả Thẻ Căn cước mới mẫu 2 vào output/output_result_moi_2.json")


if __name__ == "__main__":
    main()
