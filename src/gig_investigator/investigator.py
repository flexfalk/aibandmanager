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
	def get_nearby_cities(self):
		"""
		Returns a list of Danish cities within ~1 hour drive from Copenhagen.
		"""
		return [
			"Copenhagen", "Roskilde", "Hillerød", "Helsingør", "Køge", "Slagelse", "Næstved", "Holbæk", "Ringsted", "Frederikssund", "Helsingborg", "Greve", "Glostrup", "Ballerup", "Lyngby", "Taastrup", "Farum", "Hørsholm", "Charlottenlund", "Dragør"
		]

	def search_gigs_in_region(self, base_query: str = "live music venue", num_results_per_city: int = 8):
		"""
		Search for gig opportunities in Copenhagen and nearby cities.
		Returns a list of (city, url) tuples.
		"""
		cities = self.get_nearby_cities()
		results = []
		for city in cities:
			query = f"{base_query} {city} Denmark"
			try:
				urls = self.search_venues(query, num_results=num_results_per_city)
				for url in urls:
					results.append((city, url))
			except Exception as e:
				print(f"Search failed for {city}: {e}")
		return results

	def investigate_and_save(self, base_query: str = "live music venue", output_file: str = "gig_opportunities.csv"):
		"""
		Scour the web for possible gigs, extract info, and save to CSV.
		"""
		city_url_pairs = self.search_gigs_in_region(base_query)
		all_gigs = []
		for city, url in city_url_pairs:
			gigs = self.scrape_gig_page(url)
			for gig in gigs:
				gig_dict = {
					"Venue Name": gig.name,
					"City": city,
					"Contact Email": gig.contact_email,
					"URL": gig.url
				}
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
			response = requests.get(url)
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
