import os

import xmltodict


def count_urls_in_sitemap(file_path):
    try:
        with open(file_path, 'r') as file:
            data_dict = xmltodict.parse(file.read())
            urls = data_dict.get('urlset', {}).get('url', [])
            return len(urls)
    except Exception as e:
        print(f"Error parsing {file_path}. {e}")
        return 0


def main():
    folder_path = "pending"
    total_count = 0

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xml"):
            full_path = os.path.join(folder_path, file_name)
            count = count_urls_in_sitemap(full_path)
            print(f"{file_name}: {count} URLs")
            total_count += count

    print(f"\nTotal URLs: {total_count}")


if __name__ == "__main__":
    main()
