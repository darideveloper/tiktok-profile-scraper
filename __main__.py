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
    
    def __get_clean_counters__(self, counter:str) -> int:
        """ Convert counters like 4.5K or 4.5M to int """
        
        if "K" in counter:
            counter = int(float(counter.replace("K", "")) * 1000)
        elif "M" in counter:
            counter = int(float(counter.replace("M", "")) * 1000000)
        else:
            counter = int(counter)
            
        return counter
        
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
    
    def get_profile_details(self, profile_link: str) -> dict:
        """ Get general data of the current profile
        
        Args:
            profile_link (str): Link of the profile to extract data
        
        Returns:
            dict: General data of the profile
            {
                "followers": int,
                "following": int,
                "likes": int,
                "links": list (str),
                "videos": [
                    ...,
                    {
                        "link": str,
                        "badge": str,
                        "image": str,
                        "views": str,
                        "title": str
                    }
                ]
            }
        """
        
        selectors = {
            "video": {
                "elem": '[data-e2e="user-post-item-list"] > div',
                "link": 'a',
                "badge": '[data-e2e="video-card-badge"]',
                "image": 'picture > source',
                "views": '[data-e2e="video-views"]',
                "title": 'a[title]'
            },
            "following": '[data-e2e="following-count"]',
            "followers": '[data-e2e="followers-count"]',
            "likes": '[data-e2e="likes-count"]',
            "links": '[data-e2e="user-bio"] + div a',
        }
                
        selector_video = selectors["video"]["elem"]
        self.__load_content__(selector_video, MAX_VIDEOS, profile_link)
        
        # Get counters
        following = self.get_text(selectors["following"])
        followers = self.get_text(selectors["followers"])
        likes = self.get_text(selectors["likes"])
        
        # Fix counters
        following = self.__get_clean_counters__(following)
        followers = self.__get_clean_counters__(followers)
        likes = self.__get_clean_counters__(likes)
        
        # Get links
        links = self.get_attribs(selectors["links"], "href")
        
        # Count videos
        videos_data = []
        videos_num = self.count_elems(selector_video)
        videos_views = 0
        for video_index in range(videos_num):
            
            if video_index >= MAX_VIDEOS:
                break
            
            video_data = {}
            
            selectors_sttribs = {
                "link": 'href',
                "image": 'src',
            }
            
            selector_current_video = f'{selector_video}:nth-child({video_index + 1})'
            for selector_name, selector_value in selectors["video"].items():
                selector_elem = f'{selector_current_video} {selector_value}'
                
                # Skip elem selector
                if selector_name == "elem":
                    continue
                
                # Get elems attribs
                if selector_name in selectors_sttribs:
                    value = self.get_attrib(selector_elem, selectors_sttribs[selector_name])
                else:
                    value = self.get_text(selector_elem)
                
                video_data[selector_name] = value
                
            # Save video data
            videos_data.append(video_data)
            
            # Fix views
            video_data["views"] = self.__get_clean_counters__(video_data["views"])
        
            # Update videos reproduction
            videos_views += video_data["views"]
        
        return {
            "followers": followers,
            "following": following,
            "likes": likes,
            "links": links,
            "videos": videos_data,
            "videos_num": videos_num,
            "videos_views": videos_views,
        }
    
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
            
            profile_index = profiles.index(profile) + 1
            print(f"Profile {profile_index}/{len(profiles)}...")
            
            # Get detailed profile data
            profile_details = self.get_profile_details(profile["link"])
            
            # Save profile details
            profile = {**profile, **profile_details}            
            
            print()
            
        print()
        
        
scraper = Scraper()
scraper.autorun()