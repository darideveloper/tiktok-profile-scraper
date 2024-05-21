import os
from time import sleep
from dotenv import load_dotenv
from libs.chrome_dev import ChromDevWrapper
load_dotenv()

KEYWORDS = os.getenv("KEYWORDS")
CHROME_PATH = os.getenv("CHROME_PATH")
MAX_USERS = int(os.getenv("MAX_USERS"))
MAX_VIDEOS = int(os.getenv("MAX_VIDEOS"))


class Scraper(ChromDevWrapper):

    def __init__(self):
        """ Start chrome """
        
        # Start chrome
        super().__init__(CHROME_PATH)
        
    def __load_content__(self, selector_elem: str, max_elem: int,
                         page_url: str = "") -> int:
        """ Go down to load page content
        
        Args:
            selector_elem (str): Selector to check if the page has loaded
        
        Returns:
            int: Number of elements loaded
        """
        
        if page_url:
            self.set_page(page_url)
            sleep(3)
        
        # Go down until load al required profiles or end of the page
        while True:
            
            old_rows_num = self.count_elems(selector_elem)
            self.go_down()
            sleep(3)
            new_rows_num = self.count_elems(selector_elem)
            
            # End of the page
            if new_rows_num == old_rows_num:
                break
            
            # Max profiles reached
            if new_rows_num >= max_elem:
                break
            
        return new_rows_num
        
    def search_profiles(self):
        """ Search specific keyword in the website and load required profiles """
        
        selectors = {
            "search_bar": '[name="q"]',
            "search_button": 'button[type="submit"]',
            "accounts_tab": '[aria-controls="tabs-0-panel-search_account"]'
        }
        
        print(f"Searching profiles with the keyword: {KEYWORDS}")
        
        self.set_page("https://www.tiktok.com/")
        sleep(3)
        self.send_data(selectors["search_bar"], KEYWORDS)
        sleep(1)
        self.click(selectors["search_button"])
        sleep(2)
        self.click(selectors["accounts_tab"])
                
    def get_profiles(self) -> list:
        """ Return profiles (links and usernames) of the current search page
        
        Returns:
            list: List of profiles
            [
                {
                    "link": str,
                    "username": str,
                    "nickname": str
                    "description": str,
                    "link": str
                },
                ...
            ]
        """
        
        selectors = {
            "row": '[data-e2e="search-user-container"]',
            "username": '[data-e2e="search-user-unique-id"]',
            "nickname": '[data-e2e="search-user-nickname"]',
            "description": '[data-e2e="search-user-desc"]',
            "link": 'a',
        }
        
        print("Loading profiles...")
        
        profiles_found = self.__load_content__(selectors["row"], MAX_USERS)
        print(f"Profiles loaded: {profiles_found}")
        
        print("Getting profiles data...")
        
        profiles_data = []
        for index in range(profiles_found):
            
            profile_data = {}
            
            # Extract user data
            for selector_name, selector in selectors.items():
                selector_row = f'{selectors["row"]}:nth-child({index + 1})'
                selector_elem = f'{selector_row} {selector}'
                
                # Skip row selector
                if selector_name == "row":
                    continue
                
                # Extract text or link
                if selector_name == "link":
                    value = self.get_attrib(selector_elem, "href")
                else:
                    value = self.get_text(selector_elem)
                    
                profile_data[selector_name] = value
        
            # Clean profile data
            profile_data["nickname"] = profile_data["nickname"].split(" · ")[0].strip()
            profile_data["link"] = f'https://www.tiktok.com{profile_data["link"]}'
        
            # Save profile data
            profiles_data.append(profile_data)
            
        return profiles_data
    
    def get_profile_general_data(self, profile_link: str) -> dict:
        """ Get general data of the current profile
        
        Args:
            profile_link (str): Link of the profile to extract data
        
        Returns:
            dict: General data of the profile
            {
                "followers": int,
                "following": int,
                "likes": int,
                "links": list (str)
            }
        """
        
        selectors = {
            "videos": '[data-e2e="user-post-item-list"] > div'
        }
        
        print("Loading profile general data...")
        
        self.__load_content__(selectors["videos"], MAX_VIDEOS, profile_link)
    
    def get_profile_videos(self) -> list:
        """ Get videos (links and titles) of the current profile
        
        Returns:
            list: List of videos
            {
                "link": str,
                "title": str
            }
        """
        pass
    
    def autorun(self):
        
        self.search_profiles()
        profiles = scraper.get_profiles()
        for profile in profiles:
            profile_general_data = self.get_profile_general_data(profile["link"])
            
            print()
        
        
scraper = Scraper()
scraper.autorun()