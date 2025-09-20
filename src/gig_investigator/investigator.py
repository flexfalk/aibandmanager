from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
import pandas as pd
import os
# NOTE: The correct package for GoogleSearch is 'google-search-results', not just 'serpapi'.
from serpapi import GoogleSearch
from dotenv import load_dotenv
load_dotenv()

from dataclasses import dataclass
from typing import Optional, List
import re
import requests
from bs4 import BeautifulSoup
from src.gig_investigator.gig_opportunity import GigOpportunity


class GigInvestigator:

	@staticmethod
	def clean_gig_opportunities_llm(input_file: str = "gig_opportunities.csv", output_file: str = "gig_opportunities_cleaned_llm.csv"):
		"""
		Use an LLM to review each gig opportunity and keep only valid, relevant ones.
		"""
		import time
		from langchain.llms import OpenAI
		df = pd.read_csv(input_file)
		before = len(df)
		llm = OpenAI(temperature=0)
		exclude_list = GigInvestigator().get_exclude_list()
		exclude_str = ", ".join(exclude_list) if exclude_list else ""
		keep_rows = []
		print(f"[LLM CLEAN] Reviewing {before} rows with LLM...")
		for idx, row in df.iterrows():
			prompt = f'''
You are an expert at evaluating gig opportunities for a semi-pro band.
Given the following information, answer with a JSON object: {{"keep": true/false, "reason": "..."}}.

Venue Name: {row.get('Venue Name','')}
Contact Email: {row.get('Contact Email','')}
URL: {row.get('URL','')}

IMPORTANT: Ignore and do not keep any venues that are too large, not relevant, or appear in this list: {exclude_str}
Only keep real, relevant, and attainable opportunities for a semi-pro band.
'''
			try:
				response = llm(prompt)
				import json
				result = json.loads(response)
				if result.get("keep"):
					keep_rows.append(row)
				print(f"[LLM CLEAN] Row {idx+1}: keep={result.get('keep')} reason={result.get('reason','')} ")
			except Exception as e:
				print(f"[LLM CLEAN] Error on row {idx+1}: {e}")
			time.sleep(0.5)  # avoid rate limits
		cleaned_df = pd.DataFrame(keep_rows)
		after = len(cleaned_df)
		print(f"[LLM CLEAN] {before-after} rows removed. {after} rows remain.")
		cleaned_df.to_csv(output_file, index=False)
		print(f"[LLM CLEAN] Cleaned file saved as {output_file}.")

	@staticmethod
	def clean_gig_opportunities(input_file: str = "gig_opportunities.csv", output_file: str = "gig_opportunities_cleaned.csv"):
		"""
		Remove redundant rows and rows missing emails from the gig opportunities CSV.
		"""
		print(f"[CLEAN] Loading {input_file}...")
		df = pd.read_csv(input_file)
		before = len(df)
		# Drop rows with missing or empty emails
		df = df[df["Contact Email"].notnull() & (df["Contact Email"].str.strip() != "")]
		# Drop duplicates based on Venue Name and Contact Email
		df = df.drop_duplicates(subset=["Venue Name", "Contact Email"])
		after = len(df)
		print(f"[CLEAN] {before-after} rows removed. {after} rows remain.")
		df.to_csv(output_file, index=False)
		print(f"[CLEAN] Cleaned file saved as {output_file}.")

	def get_exclude_list(self, exclude_file: str = "exclude_list.md"):
		"""
		Read a list of venues or keywords to exclude from a markdown file (one per line, skip comments/empty lines).
		"""
		excludes = []
		try:
			with open(exclude_file, encoding="utf-8") as f:
				for line in f:
					line = line.strip()
					if line and not line.startswith("#"):
						excludes.append(line)
		except Exception as e:
			print(f"[WARN] Could not read exclude list from {exclude_file}: {e}")
		return excludes

	def get_manual_venues(self, venue_file: str = "venue_list.md"):
		"""
		Read a list of venue names from a markdown file (one per line, skip comments/empty lines).
		"""
		venues = []
		try:
			with open(venue_file, encoding="utf-8") as f:
				for line in f:
					line = line.strip()
					if line and not line.startswith("#"):
						venues.append(line)
		except Exception as e:
			print(f"[WARN] Could not read manual venue list from {venue_file}: {e}")
		return venues
	def extract_venue_info_with_llm(self, html: str, url: str) -> dict:
		"""
		Use an LLM to extract venue info from preprocessed HTML/text. Returns dict with keys: is_venue, venue_name, contact_email, contact_page_url, etc.
		"""
		from bs4 import BeautifulSoup, Comment
		soup = BeautifulSoup(html, "html.parser")
		# Remove scripts, styles, meta, noscript, comments
		for tag in soup(["script", "style", "meta", "noscript"]):
			tag.decompose()
		for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
			comment.extract()
		# Extract title, headings, and visible text
		title = soup.title.string.strip() if soup.title and soup.title.string else ""
		headings = " ".join([h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])])
		links = " ".join([a.get_text(strip=True) for a in soup.find_all("a")])
		body_text = soup.get_text(separator=" ", strip=True)
		# Compose a compact context
		compact_text = f"Title: {title}\nHeadings: {headings}\nLinks: {links[:500]}\nBody: {body_text[:3000]}"
		llm = OpenAI(temperature=0)
		exclude_list = self.get_exclude_list()
		exclude_str = ", ".join(exclude_list) if exclude_list else ""
		prompt = (
			"""
			You are an expert at extracting information about music venues from web pages.
			Given the following web page content, answer the following questions:

			1. Is this page for a real music venue? (yes/no)
			2. What is the venue's name?
			3. What is the best contact email (if any)?
			4. What is the main URL for the venue?
			5. If you can't find the info, suggest a likely contact page URL (if any).

			IMPORTANT: Ignore and do not return any information about these venues or pages, as they are too large or not relevant for a semi-pro band: {exclude_str}

			Return your answer as a JSON object with keys: is_venue, venue_name, contact_email, main_url, contact_page_url.

			PAGE CONTENT:
			{context}
			"""
		)
		full_prompt = prompt.format(context=compact_text, exclude_str=exclude_str)
		response = llm(full_prompt)
		import json
		try:
			info = json.loads(response)
		except Exception:
			info = {"is_venue": "unknown", "venue_name": None, "contact_email": None, "main_url": url, "contact_page_url": None}
		return info

	def smart_scrape_gig_page(self, url: str) -> dict:
		"""
		Scrape a page, use LLM to extract venue info, and follow contact page if needed.
		"""
		headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
		try:
			response = requests.get(url, headers=headers, timeout=10)
			response.raise_for_status()
		except Exception as e:
			print(f"Failed to fetch {url}: {e}")
			return None
		info = self.extract_venue_info_with_llm(response.text, url)
		if info.get("is_venue", "no").lower() != "yes" and info.get("contact_page_url"):
			# Try the contact page if suggested
			contact_url = info["contact_page_url"]
			if not contact_url.startswith("http"):
				from urllib.parse import urljoin
				contact_url = urljoin(url, contact_url)
			try:
				contact_resp = requests.get(contact_url, headers=headers, timeout=10)
				contact_resp.raise_for_status()
			except Exception as e:
				print(f"Failed to fetch contact page {contact_url}: {e}")
				return info
			contact_info = self.extract_venue_info_with_llm(contact_resp.text, contact_url)
			# Prefer info from contact page if available
			for k, v in contact_info.items():
				if v and (not info.get(k) or info[k] == "unknown"):
					info[k] = v
		return info
	def search_gigs_in_copenhagen(self, queries=None, num_results_per_query: int = 10, max_queries: int = 10, include_manual_venues: bool = True):
		"""
		Search for gig opportunities in Copenhagen using Danish queries.
		Returns a list of (query, url) tuples.
		"""
		if queries is None:
			queries = [
				"spillesteder københavn",
				"live musik københavn",
				"koncerter københavn",
				"musiksteder københavn",
				"booking af band københavn"
			]
		if include_manual_venues:
			manual_venues = self.get_manual_venues()
			queries.extend(manual_venues)
		results = []
		print(f"[INFO] Starting search for gig venues in Copenhagen with up to {max_queries} queries...")
		for i, query in enumerate(queries):
			if i >= max_queries:
				print(f"[INFO] Reached max query limit ({max_queries}). Stopping search loop.")
				break
			print(f"[SEARCH] Query {i+1}/{min(len(queries), max_queries)}: '{query}'")
			try:
				urls = self.search_venues(query, num_results=num_results_per_query)
				print(f"[RESULT] Found {len(urls)} URLs for query '{query}'")
				for url in urls:
					results.append((query, url))
			except Exception as e:
				print(f"[ERROR] Search failed for query '{query}': {e}")
		print(f"[INFO] Search complete. Total query-url pairs: {len(results)}")
		return results

	def investigate_and_save(self, output_file: str = "gig_opportunities.csv"):
		"""
		Scour the web for possible gigs in Copenhagen using Danish queries, extract info with LLM, and save to CSV.
		"""
		query_url_pairs = self.search_gigs_in_copenhagen(max_queries=10, include_manual_venues=True)
		all_gigs = []
		print(f"[INFO] Starting LLM-based extraction for {len(query_url_pairs)} URLs...")
		for idx, (query, url) in enumerate(query_url_pairs):
			print(f"[SCRAPE] ({idx+1}/{len(query_url_pairs)}) Scraping URL: {url}")
			info = self.smart_scrape_gig_page(url)
			print(f"[LLM] Extraction result: {info}")
			if info and info.get("is_venue", "no").lower() == "yes":
				gig_dict = {
					"Venue Name": info.get("venue_name"),
					"Query": query,
					"Contact Email": info.get("contact_email"),
					"URL": info.get("main_url", url)
				}
				print(f"[FOUND] {gig_dict}")
				all_gigs.append(gig_dict)
		if all_gigs:
			print(f"[SUCCESS] Saving {len(all_gigs)} gig opportunities to {output_file}")
			pd.DataFrame(all_gigs).drop_duplicates().to_csv(output_file, index=False)
		else:
			print("[INFO] No gig opportunities found.")

	def __init__(self):
		"""
		Investigates web pages for gig opportunities and extracts contact info.
		"""
		pass

	def search_venues(self, query: str, num_results: int = 10) -> list:
		"""
		Search the internet for venue places using SerpAPI and return a list of URLs.
		"""
		api_key = os.getenv("SERPAPI_API_KEY")
		if not api_key:
			raise ValueError("SERPAPI_API_KEY not set in environment.")

		params = {
			"engine": "google",
			"q": query,
			"num": num_results,
			"api_key": api_key
		}
		search = GoogleSearch(params)
		results = search.get_dict()
		urls = []
		for res in results.get("organic_results", []):
			link = res.get("link")
			if link:
				urls.append(link)
		return urls

	def scrape_gig_page(self, url: str) -> List[GigOpportunity]:
		"""
		Scrape a web page for gig opportunities and extract emails.
		Returns a list of GigOpportunity objects.
		"""
		try:
			headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
			response = requests.get(url, headers=headers)
			response.raise_for_status()
		except Exception as e:
			print(f"Failed to fetch {url}: {e}")
			return []

		soup = BeautifulSoup(response.text, 'html.parser')
		text = soup.get_text()
		emails = set(re.findall(r"[\w\.-]+@[\w\.-]+", text))

		# For now, just create a GigOpportunity for each email found
		gigs = []
		for email in emails:
			gigs.append(GigOpportunity(
				name="Unknown",
				contact_email=email,
				url=url
			))
		return gigs
	


if __name__ == "__main__":
	# Example test URL (replace with a real page containing emails for real test)
	test_url = "https://www.example.com"
	investigator = GigInvestigator()
	gigs = investigator.scrape_gig_page(test_url)
	for gig in gigs:
		print(gig)
