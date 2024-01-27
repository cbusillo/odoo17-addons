import logging
import re
from string import capwords
from urllib.parse import urlparse

import requests

# noinspection PyPackageRequirements
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed

from odoo import api, fields, models

BASE_URL = "https://www.crowleymarine.com"


class ProductScraperURLState(models.Model):
    _name = "product.scraper.url.state"
    _description = "URL Scraping State"

    url = fields.Char(string="URL", required=True, index=True)
    scraped = fields.Boolean(default=False, index=True)

    _sql_constraints = [("url_unique", "UNIQUE(url)", "The URL must be unique!")]


class ProductScraperSource(models.Model):
    _name = "product.scraper.source"
    _description = "Product Scraper Source URL"

    source_url = fields.Char(index=True, string="Source URL")
    source_url_display = fields.Char(compute="_compute_source_url_display", store=True, index=True)
    product_id = fields.Many2one("product.scraper", string="Related Product", index=True)

    _sql_constraints = [("product_source_unique", "UNIQUE(source_url, product_id)", "The Source URL must be unique per product!")]

    @api.depends("source_url")
    def _compute_source_url_display(self):
        for record in self:
            record.source_url = record.source_url or ""
            record.source_url_display = record.source_url.replace(BASE_URL, "")


class ProductScraper(models.Model):
    _name = "product.scraper"
    _description = "Product Scraper"

    name = fields.Char()
    source_url_ids = fields.One2many("product.scraper.source", "product_id", string="Source URL Count", index=True)
    source_url_count = fields.Integer(compute="_compute_source_url_count", store=True)
    source_url_list = fields.Text(compute="_compute_source_url_list", string="Source URLs List")
    source_url_html = fields.Text(compute="_compute_source_url_html", string="Source URLs HTML")
    url = fields.Char(string="URL", index=True)
    url_display = fields.Char(compute="_compute_url_display", string="Path")
    sku = fields.Char(required=True, string="SKU", index=True)
    price = fields.Float(index=True)
    brand = fields.Char(index=True)
    product_ids = fields.One2many("product.product", "product_scraper_id", string="Related Products")

    _sql_constraints = [("brand_sku_unique", "UNIQUE(brand, sku)", "The Brand and SKU must be unique!")]

    @api.depends("source_url_ids")
    def _compute_source_url_list(self):
        for record in self:
            record.source_url_list = "\n".join(url.source_url_display for url in record.source_url_ids)

    @api.depends("source_url_ids")
    def _compute_source_url_count(self):
        for rec in self:
            rec.source_url_count = len(rec.source_url_ids)

    @api.depends("url")
    def _compute_url_display(self):
        for record in self:
            record.url = record.url or ""
            record.url_display = record.url.replace(BASE_URL, "")

    @api.depends("source_url_ids")
    def _compute_source_url_html(self):
        def format_header(header):
            return f"<th style='border:1px solid black; padding:10px;'>{header}</th>"

        def format_cell(index, cell, cells_len):
            if index == cells_len - 2:
                return cell.upper()
            elif index == cells_len - 1:
                return capwords(cell).replace("-", " ")
            elif index == cells_len - 3:
                return cell.upper()
            else:
                return capwords(cell).replace("Oem-parts", "OEM")

        headers = ["Brand", "Type", "", "Year", "Model"]  # Replace with your actual headers
        header_row = f"<tr>{''.join(format_header(header) for header in headers)}</tr>"

        for record in self:
            urls = (url.source_url_display for url in record.source_url_ids)

            table_rows = []
            for url in urls:
                cells = url.split("/")[1:]  # Skip the first cell if it's blank
                formatted_cells = [format_cell(index, cell, len(cells)) for index, cell in enumerate(cells)]
                table_rows.append(
                    "<tr>"
                    + "".join(f"<td style='border:1px solid black; padding:10px;'>{cell}</td>" for cell in formatted_cells)
                    + "</tr>"
                )  # pylint: disable=consider-using-f-string

            record.source_url_html = f"<table style='border:1px solid black'>{header_row + ''.join(table_rows)}</table>"

    @staticmethod
    def extract_product_details(sku_element, price_element, name_element):
        if sku_element:
            sku = sku_element.text.strip()
        else:
            sku = None

        if price_element:
            price_str = price_element.text.strip()
            # noinspection RegExpRedundantEscape
            price = re.sub(r"[^\d\.]", "", str(price_str))
            if price == "":
                price = 0.0
            else:
                # Handle price ranges
                if "to" in price:
                    price = [float(p) for p in price.split("to")][0]
                else:
                    price = float(price)
        else:
            price = 0.0

        if name_element:
            name = name_element.text.strip()
        else:
            name = ""

        if not sku or price is None or not name:
            sku = sku or ".check-me"

        return sku, price, name

    @api.model
    def scrape_website(self):
        visited_urls = set()
        visited_end_links = set()

        @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
        def get(url):
            http_response = requests.get(url, timeout=10)
            if http_response.status_code != 404:  # Only raise if status code is not 404
                http_response.raise_for_status()  # Raises a HTTPError if one occurred
            return http_response

        logger = logging.getLogger(__name__)

        def create_or_update_product(product_sku, product_price, product_name, product_brand, product_end_link):
            scraped_product_data = {
                "name": capwords(product_name),
                "url": product_end_link,
                "sku": product_sku,
                "price": product_price,
                "brand": product_brand,
            }
            logger.info("Checking product: %s", scraped_product_data)
            # Search for existing product
            product = self.search([("sku", "=", product_sku), ("brand", "=", product_brand)], limit=1)

            if product:
                # Update product if it exists
                product.write(
                    {
                        "name": scraped_product_data["name"],
                        "price": scraped_product_data["price"],
                    }
                )
                logger.info("Updated product: %s", scraped_product_data)
            else:
                # Create product if it does not exist
                product = self.create(scraped_product_data)
                logger.info("Created new product: %s", scraped_product_data)
                self.env.cr.commit()  # pylint: disable=invalid-commit

            # Check if source_url already exists for the product
            source_exists = self.env["product.scraper.source"].search(
                [("source_url", "=", part_link), ("product_id", "=", product.id)], limit=1
            )

            if not source_exists:
                # Add source_url to product
                self.env["product.scraper.source"].create(
                    {
                        "source_url": part_link,
                        "product_id": product.id,
                    }
                )
                logger.info("Added source URL %s to product %s", part_link, product.name)
                self.env.cr.commit()  # pylint: disable=invalid-commit
            else:
                logger.info("Source URL %s already exists for product %s", part_link, product.name)

            visited_end_links.add(product_end_link)

        def get_links_in_page(url: str, search_regex: str = r"/((19|20)\d{2}|ag|af|ab|aa)") -> list:
            if BASE_URL not in url:
                url = BASE_URL + url.replace("file://", "")

            if url in visited_urls and url != BASE_URL:
                logger.info("Already visited: %s", url)
                return []

            logger.info("Visiting: %s", url)
            try:
                http_response = get(url)
            except requests.exceptions.HTTPError as http_error:
                logger.error("Error during requests to %s : %s", url, str(http_error))
                return []
            soup_result = BeautifulSoup(http_response.text, "html.parser")
            visited_urls.add(url)

            links = [
                (BASE_URL + link.get("href")) if link.get("href").startswith("/") else link.get("href")
                for link in soup_result.find_all("a")
                if link.get("href")
            ]

            filtered_links = [link.split("?")[0].split("#")[0] for link in links if re.search(search_regex, link)]

            return filtered_links

        def get_links_in_page_year(url: str) -> list:
            return get_links_in_page(url)

        def get_links_in_page_product(url: str) -> list:
            return get_links_in_page(url, r"/products/")

        def get_links_in_page_main(url: str) -> list:
            return get_links_in_page(url, r"/oem-parts")

        for main_link in get_links_in_page_main(BASE_URL):
            if "oem-parts" not in main_link:
                continue
            for type_year_link in get_links_in_page_year(main_link):
                if "outboard" not in type_year_link and "international" not in type_year_link:
                    continue
                for motor_link in get_links_in_page_year(type_year_link):
                    url_state = self.env["product.scraper.url.state"].search([("url", "=", motor_link)], limit=1)
                    if url_state and url_state.scraped:
                        logger.info("Link %s already scraped, skipping...", motor_link)
                        continue
                    for part_link in get_links_in_page_year(motor_link):
                        if "/products/" in part_link:
                            continue
                        for end_link in get_links_in_page_product(part_link):
                            brand = capwords(urlparse(end_link).path.split("/")[1])
                            if end_link in visited_end_links:
                                continue
                            else:
                                try:
                                    response = get(end_link)
                                except requests.exceptions.HTTPError as error:
                                    logger.error("Error during requests to %s : %s", end_link, str(error))
                                    continue
                                soup = BeautifulSoup(response.text, "html.parser")
                                variant_bool = "Product Variations available" in soup.text

                                if variant_bool:
                                    variants = soup.select("#variationsTablewrap > table tr")
                                    for variant in variants:
                                        if "id" not in variant.contents[1].attrs:
                                            continue
                                        if "variations" not in variant.contents[1].attrs.get("id"):
                                            continue
                                        name_element = variant.contents[3].contents[0]
                                        sku_element = variant.contents[5].contents[0]
                                        price_element = variant.contents[1].contents[5].contents[3].contents[0]
                                        sku, price, name = self.extract_product_details(sku_element, price_element, name_element)
                                        create_or_update_product(sku, price, name, brand, end_link)
                                else:
                                    # noinspection SpellCheckingInspection
                                    sku_element = soup.select_one('small[itemprop="sku"], span[data-testid="product:sku"]')

                                    price_element = soup.select_one('span[itemprop="price"]')

                                    name_element = soup.select_one('span[itemprop="name"]')

                                    sku, price, name = self.extract_product_details(sku_element, price_element, name_element)
                                    create_or_update_product(sku, price, name, brand, end_link)

                    if not url_state:
                        # if the URL wasn't previously in the database, create a new record
                        url_state = self.env["product.scraper.url.state"].create({"url": motor_link})
                    url_state.write({"scraped": True})
                    self.env.cr.commit()  # pylint: disable=invalid-commit
