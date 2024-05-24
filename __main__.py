import os
import csv
from time import sleep
from dotenv import load_dotenv
from libs.chrome_dev import ChromDevWrapper
load_dotenv()

KEYWORDS = os.getenv("KEYWORDS").split(",")
CHROME_PATH = os.getenv("CHROME_PATH")
MAX_USERS = int(os.getenv("MAX_USERS"))
MAX_VIDEOS = int(os.getenv("MAX_VIDEOS"))
DEBUG = os.getenv("DEBUG") == "True"


class Scraper(ChromDevWrapper):

    def __init__(self):
        """ Start chrome """
        
        # Start chrome
        super().__init__(CHROME_PATH)
        
        # Csv paths
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.profiles_path = os.path.join(current_path, "output", "profiles.csv")
        self.videos_path = os.path.join(current_path, "output", "videos.csv")
        
        # Delete csv files in debug mode
        if DEBUG:
            if os.path.exists(self.profiles_path):
                os.remove(self.profiles_path)
            if os.path.exists(self.videos_path):
                os.remove(self.videos_path)
        
        # Create initial csv files
        self.__create_profiles_csv__()
        self.__create_videos_csv__()
        
        # Control variables
        self.scraped_profiles = self.__get_csv_scraped_profiles__()
        
    def __create_profiles_csv__(self):
        """ Create profiles csv file if not exists """
        
        if os.path.exists(self.profiles_path):
            return None
        
        with open(self.profiles_path, "w", newline='') as file:
            columns = [
                "keywords",
                "username",
                "nickname",
                "description",
                "profile_link",
                "followers",
                "following",
                "likes",
                "videos_num",
                "videos_views"
            ]
            csv_file = csv.writer(file)
            csv_file.writerow(columns)
            
    def __create_videos_csv__(self):
        """ Create videos csv file if not exists """
        
        if os.path.exists(self.videos_path):
            return None
            
        with open(self.videos_path, "w", newline='') as file:
            columns = [
                "username",
                "link",
                "badge",
                "image",
                "views",
                "title"
            ]
            csv_file = csv.writer(file)
            csv_file.writerow(columns)
            
    def __get_csv_scraped_profiles__(self) -> list:
        """ get scraped profiles from csv file

        Returns:
            list: List of usernames
        """
        
        with open(self.profiles_path, "r", encoding="utf-8") as file:
            csv_file = csv.reader(file)
            next(csv_file)
            scraped_profiles = [row[1] for row in csv_file]
            
        return scraped_profiles
            
        
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
        
        if not counter:
            return 0
        
        if "K" in counter:
            counter = int(float(counter.replace("K", "")) * 1000)
        elif "M" in counter:
            counter = int(float(counter.replace("M", "")) * 1000000)
        elif "B" in counter:
            counter = int(float(counter.replace("B", "")) * 1000000000)
        else:
            counter = int(counter)
            
        return counter
        
    def search_profiles(self, keyword: str):
        """ Search specific keyword in the website and load required profiles 
        
        Args:
            keyword (str): Keyword to search
        """
        
        selectors = {
            "search_bar": '[name="q"]',
            "search_button": 'button[type="submit"]',
            "accounts_tab": '[aria-controls="tabs-0-panel-search_account"]'
        }
                
        print(f"\n\nSearching profiles with the keyword: {keyword}")
        
        # Load page
        self.set_page("https://www.tiktok.com/")
        
        # Search in page
        sleep(3)
        self.send_data(selectors["search_bar"], keyword)
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
            
            if len(profiles_data) >= MAX_USERS:
                break
            
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
                
            # Skip profile if already scraped
            if profile_data["username"] in self.scraped_profiles:
                print(f"\t\tProfile {profile_data['username']} already scraped")
                continue
            self.scraped_profiles.append(profile_data["username"])
        
            # Clean profile data
            profile_data["nickname"] = profile_data["nickname"].split(" · ")[0].strip()
            profile_data["link"] = f'https://www.tiktok.com{profile_data["link"]}'
            profile_data["description"] = profile_data["description"].strip().replace("\n", " ")
        
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
                "image": 'img',
                "views": '[data-e2e="video-views"]',
                "title": 'a[title]'
            },
            "following": '[data-e2e="following-count"]',
            "followers": '[data-e2e="followers-count"]',
            "likes": '[data-e2e="likes-count"]',
        }
                
        selector_video = selectors["video"]["elem"]
        self.__load_content__(selector_video, MAX_VIDEOS, profile_link)
        
        # Set zoom and wait
        self.set_zoom(0.1)
        sleep(5)
        
        # Get counters
        following = self.get_text(selectors["following"])
        followers = self.get_text(selectors["followers"])
        likes = self.get_text(selectors["likes"])
        
        # Fix counters
        following = self.__get_clean_counters__(following)
        followers = self.__get_clean_counters__(followers)
        likes = self.__get_clean_counters__(likes)
        
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
    
    def save_profile(self, username: str, nickname: str, description: str,
                     profile_link: str, followers: int, following: int, likes: int, 
                     videos_num: int, videos_views: int, keyword: str):
        """ Save in csv profile data of a single user 
        
        Args:
            username (str): Username of the profile
            nickname (str): Nickname of the profile
            description (str): Description of the profile
            profile_link (str): Link of the profile
            followers (int): Number of followers
            following (int): Number of following
            likes (int): Number of likes
            videos_num (int): Number of videos
            videos_views (int): Number of videos views
            keyword (str): Keyword used to search the profile
        """
        
        with open(self.profiles_path, "a", encoding="utf-8", newline='') as file:
            csv_file = csv.writer(file)
            row = [
                keyword,
                username,
                nickname,
                description,
                profile_link,
                followers,
                following,
                likes,
                videos_num,
                videos_views
            ]
            csv_file.writerow(row)
    
    def save_videos(self, username: str, videos_data: list):
        """ Save in csv video data of a single user 
        
        Args:
            username (str): Username of the profile
            videos_data (list): List of videos
            [
                {
                    "link": str,
                    "badge": str,
                    "image": str,
                    "views": str,
                    "title": str
                },
                ...
            ]
        """
        
        with open(self.videos_path, "a", encoding="utf-8", newline='') as file:
            csv_file = csv.writer(file)
            for video_data in videos_data:
                row = [
                    username,
                    video_data["link"],
                    video_data["badge"],
                    video_data["image"],
                    video_data["views"],
                    video_data["title"]
                ]
                csv_file.writerow(row)
    
    def autorun(self):
        
        for keyword in KEYWORDS:
        
            self.search_profiles(keyword)
            profiles = scraper.get_profiles()
            for profile in profiles:
                
                profile_index = profiles.index(profile) + 1
                print(f"\tProfile {profile_index}/{len(profiles)} ({profile['username']})...")
                
                # Get detailed profile data
                profile_details = self.get_profile_details(profile["link"])
                
                # Save profile details
                self.save_profile(
                    profile["username"],
                    profile["nickname"],
                    profile["description"],
                    profile["link"],
                    profile_details["followers"],
                    profile_details["following"],
                    profile_details["likes"],
                    profile_details["videos_num"],
                    profile_details["videos_views"],
                    keyword,
                )
                
                # Save videos details
                self.save_videos(profile["username"], profile_details["videos"])
                            
        print("Finished!")
        
        
scraper = Scraper()
scraper.autorun()