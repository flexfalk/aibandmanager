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
	def search_gigs_in_copenhagen(self, queries=None, num_results_per_query: int = 10):
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
		results = []
		for query in queries:
			try:
				urls = self.search_venues(query, num_results=num_results_per_query)
				for url in urls:
					results.append((query, url))
			except Exception as e:
				print(f"Search failed for query '{query}': {e}")
		return results

	def investigate_and_save(self, output_file: str = "gig_opportunities.csv"):
		"""
		Scour the web for possible gigs in Copenhagen using Danish queries, extract info, and save to CSV.
		"""
		query_url_pairs = self.search_gigs_in_copenhagen()
		all_gigs = []
		for query, url in query_url_pairs:
			gigs = self.scrape_gig_page(url)
			for gig in gigs:
				gig_dict = {
					"Venue Name": gig.name,
					"Query": query,
					"Contact Email": gig.contact_email,
					"URL": gig.url
				}
				print(gig_dict)
				all_gigs.append(gig_dict)
		if all_gigs:
			print(f"Saving {len(all_gigs)} gig opportunities to {output_file}")
			pd.DataFrame(all_gigs).drop_duplicates().to_csv(output_file, index=False)
		else:
			print("No gig opportunities found.")

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
