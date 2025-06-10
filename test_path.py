import os

# config.pyで設定されているTHUMBNAIL_FOLDERのパスをそのまま貼り付けます
# 例: F:\dev\BrogDev\static\uploads\thumbnails
THUMBNAIL_BASE_PATH = r"F:\dev\BrogDev\static\uploads\thumbnails"

# ここに、あなたがFlaskでアップロードしたにもかかわらず表示されない
# 実際のサムネイルファイル名を正確に貼り付けてください。
# 最新のログからは「thumb_7f4c294b-14e7-43c8-a13f-2c3511e16342_DSC_0056.png」が該当します。
TARGET_FILENAME = "thumb_7f4c294b-14e7-43c8-a13f-2c3511e16342_DSC_0056.png"

full_path = os.path.join(THUMBNAIL_BASE_PATH, TARGET_FILENAME)

print(f"Checking path: {full_path}")
print(f"Does file exist? {os.path.exists(full_path)}")

# さらに、フォルダ自体が存在するか確認
print(f"Does base folder exist? {os.path.exists(THUMBNAIL_BASE_PATH)}")

# フォルダの中身をリストアップして、ファイル名が存在するか確認
if os.path.exists(THUMBNAIL_BASE_PATH) and os.path.isdir(THUMBNAIL_BASE_PATH):
    print(f"Files in base folder: {os.listdir(THUMBNAIL_BASE_PATH)}")
    if TARGET_FILENAME in os.listdir(THUMBNAIL_BASE_PATH):
        print(f"TARGET_FILENAME found in folder listing!")
    else:
        print(f"TARGET_FILENAME NOT found in folder listing. Possible mismatch.")
        # 大文字小文字を区別しない検索 (Windowsは通常区別しないが念のため)
        found_case_insensitive = False
        for f in os.listdir(THUMBNAIL_BASE_PATH):
            if f.lower() == TARGET_FILENAME.lower():
                print(f"Found file with case-insensitive match: {f}")
                found_case_insensitive = True
                break
        if not found_case_insensitive:
            print("No case-insensitive match found either.")