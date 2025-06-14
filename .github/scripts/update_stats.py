#!/usr/bin/env python3
"""
GitHub Coding Statistics Generator for DhruvDoshi
Updates README.md with coding statistics automatically
"""

import os
import requests
import re
from datetime import datetime, timedelta
from dateutil import parser

class GitHubStatsGenerator:
    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN')
        self.username = os.environ.get('GITHUB_USERNAME', 'DhruvDoshi')
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHubStatsBot'
        }
        self.stats = {
            'today': {'additions': 0, 'deletions': 0, 'commits': 0},
            'week': {'additions': 0, 'deletions': 0, 'commits': 0},
            'month': {'additions': 0, 'deletions': 0, 'commits': 0},
            'year': {'additions': 0, 'deletions': 0, 'commits': 0},
            'overall': {'additions': 0, 'deletions': 0, 'commits': 0}
        }
    
    def get_user_repos(self):
        """Get all repositories for the user including organizations"""
        repos = []
        
        # Get user's own repositories
        page = 1
        while True:
            url = f'https://api.github.com/users/{self.username}/repos'
            params = {'page': page, 'per_page': 100, 'sort': 'updated', 'type': 'all'}
            
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                
                page_repos = response.json()
                if not page_repos:
                    break
                    
                repos.extend(page_repos)
                page += 1
                
            except Exception as e:
                print(f"Error fetching user repos: {e}")
                break
        
        # Get repositories from organizations where user has contributed
        try:
            url = f'https://api.github.com/user/repos'
            params = {'type': 'all', 'per_page': 100, 'sort': 'updated'}
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                org_repos = response.json()
                for repo in org_repos:
                    if repo['full_name'] not in [r['full_name'] for r in repos]:
                        repos.append(repo)
        except Exception as e:
            print(f"Error fetching org repos: {e}")
        
        print(f"Total repositories found: {len(repos)}")
        return repos
    
    def get_commit_activity(self, repo_full_name):
        """Get commit activity for a repository with better pagination"""
        commits_data = []
        page = 1
        
        # Get commits from the last 2 years for better overall stats
        since_date = (datetime.now() - timedelta(days=730)).isoformat()
        
        while page <= 20:  # Increased page limit for better coverage
            url = f'https://api.github.com/repos/{repo_full_name}/commits'
            params = {
                'author': self.username,
                'since': since_date,
                'page': page,
                'per_page': 100
            }
            
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                if response.status_code == 409:  # Empty repository
                    break
                    
                response.raise_for_status()
                commits = response.json()
                
                if not commits:
                    break
                
                print(f"  Processing page {page} with {len(commits)} commits...")
                
                for commit in commits:
                    # Get detailed commit info
                    commit_detail = self.get_commit_details(repo_full_name, commit['sha'])
                    if commit_detail:
                        commits_data.append({
                            'date': commit['commit']['author']['date'],
                            'stats': commit_detail
                        })
                
                page += 1
                
                # Add small delay to avoid rate limiting
                import time
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error fetching commits for {repo_full_name}: {e}")
                break
        
        return commits_data
    
    def get_commit_details(self, repo_full_name, sha):
        """Get detailed stats for a specific commit"""
        url = f'https://api.github.com/repos/{repo_full_name}/commits/{sha}'
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            commit_data = response.json()
            stats = commit_data.get('stats', {})
            
            return {
                'additions': stats.get('additions', 0),
                'deletions': stats.get('deletions', 0),
                'total': stats.get('total', 0)
            }
            
        except Exception as e:
            print(f"Error fetching commit details: {e}")
            return None
    
    def get_contribution_calendar(self):
        """Get contribution data using GraphQL API for more comprehensive stats"""
        query = """
        query($username: String!) {
          user(login: $username) {
            contributionsCollection {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    contributionCount
                    date
                  }
                }
              }
            }
          }
        }
        """
        
        url = 'https://api.github.com/graphql'
        headers = {**self.headers, 'Accept': 'application/vnd.github.v4+json'}
        
        try:
            response = requests.post(
                url, 
                json={'query': query, 'variables': {'username': self.username}},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                calendar = data['data']['user']['contributionsCollection']['contributionCalendar']
                print(f"📈 GitHub shows total contributions: {calendar['totalContributions']}")
                return calendar
        except Exception as e:
            print(f"GraphQL query failed: {e}")
        
        return None
        """Determine which time categories this commit falls into"""
        try:
            commit_date = parser.parse(commit_date_str)
            now = datetime.now(commit_date.tzinfo)
            
            time_diff = now - commit_date
            categories = []
            
            # Today (last 24 hours)
            if time_diff.days == 0:
                categories.append('today')
            
            # This week (last 7 days)
            if time_diff.days < 7:
                categories.append('week')
            
            # This month (last 30 days)
            if time_diff.days < 30:
                categories.append('month')
            
            # This year (last 365 days)
            if time_diff.days < 365:
                categories.append('year')
            
            # Overall
            categories.append('overall')
            
            return categories
            
        except Exception as e:
            print(f"Error parsing date {commit_date_str}: {e}")
            return ['overall']
    
    def analyze_repositories(self):
        """Analyze all repositories and gather statistics"""
        print(f"Starting analysis for user: {self.username}")
        
        repos = self.get_user_repos()
        
        # Process all repos, not just limited ones for better overall stats
        active_repos = sorted(repos, key=lambda x: x.get('updated_at', ''), reverse=True)
        
        print(f"Will analyze {len(active_repos)} repositories...")
        
        for i, repo in enumerate(active_repos):
            repo_name = repo['full_name']
            print(f"\nAnalyzing repository {i+1}/{len(active_repos)}: {repo_name}")
            
            if repo.get('size', 0) == 0:  # Skip empty repos
                print("  Skipping empty repository")
                continue
            
            commits = self.get_commit_activity(repo_name)
            print(f"  Found {len(commits)} commits in {repo['name']}")
            
            for commit in commits:
                categories = self.categorize_by_time(commit['date'])
                stats = commit['stats']
                
                for category in categories:
                    self.stats[category]['additions'] += stats['additions']
                    self.stats[category]['deletions'] += stats['deletions']
                    self.stats[category]['commits'] += 1
            
            # Show progress
            if (i + 1) % 5 == 0:
                print(f"\n📊 Progress Update - Processed {i+1} repos:")
                print(f"   Overall: {self.stats['overall']['commits']} commits, +{self.stats['overall']['additions']} -{self.stats['overall']['deletions']}")
        
        print(f"\n🎯 Analysis complete! Processed {len(active_repos)} repositories.")
    
    def format_number(self, num):
        """Format number with commas for readability"""
        return f"{num:,}"
    
    def generate_stats_table(self):
        """Generate properly formatted markdown table with statistics"""
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Start with proper markdown table formatting
        table = "## Coding Statistics 📊\n\n"
        table += "| Period | Lines Added | Lines Removed | Net Lines | Commits |\n"
        table += "|--------|-------------|---------------|-----------|---------|\n"
        
        periods = {
            'today': 'Today',
            'week': 'This Week',
            'month': 'This Month', 
            'year': 'This Year',
            'overall': 'Overall'
        }
        
        for key, label in periods.items():
            stats = self.stats[key]
            net_lines = stats['additions'] - stats['deletions']
            net_sign = '+' if net_lines >= 0 else ''
            
            # Properly format each cell with spaces
            table += f"| {label} | {self.format_number(stats['additions'])} | {self.format_number(stats['deletions'])} | {net_sign}{self.format_number(net_lines)} | {self.format_number(stats['commits'])} |\n"
        
        table += f"\n*Last updated: {current_time}*\n"
        return table
    
    def update_readme(self):
        """Update README.md with new statistics"""
        readme_path = 'README.md'
        
        if not os.path.exists(readme_path):
            print("README.md not found!")
            return False
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_stats = self.generate_stats_table()
        
        # Pattern to match existing stats section
        stats_pattern = r'## Coding Statistics 📊.*?(?=\n## |\n\[|\Z)'
        
        if re.search(stats_pattern, content, re.DOTALL):
            # Replace existing stats section
            content = re.sub(stats_pattern, new_stats.rstrip(), content, flags=re.DOTALL)
            print("Updated existing statistics section")
        else:
            # Insert after Github Languages and Status section
            insert_pattern = r'(## Github Languages and Status.*?</p>)'
            if re.search(insert_pattern, content, re.DOTALL):
                content = re.sub(
                    insert_pattern, 
                    r'\1\n\n' + new_stats, 
                    content, 
                    flags=re.DOTALL
                )
                print("Added new statistics section after Github stats")
            else:
                # Insert before Top Blog Posts section
                blog_pattern = r'(## Top Blog Posts)'
                if blog_pattern in content:
                    content = content.replace('## Top Blog Posts', new_stats + '\n## Top Blog Posts')
                    print("Added new statistics section before blog posts")
                else:
                    print("Could not find suitable location to insert stats")
                    return False
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("README.md updated successfully!")
        return True
    
    def run(self):
        """Main execution method"""
        if not self.token:
            print("Error: GITHUB_TOKEN environment variable is required")
            return
        
        print("🚀 Starting GitHub Coding Statistics Generator")
        print(f"📊 Analyzing repositories for: {self.username}")
        
        try:
            # Get contribution calendar for reference
            calendar = self.get_contribution_calendar()
            
            # Analyze repositories
            self.analyze_repositories()
            
            print("\n📈 Final Statistics Summary:")
            for period, stats in self.stats.items():
                net = stats['additions'] - stats['deletions']
                print(f"  {period.capitalize()}: {stats['commits']} commits, "
                      f"+{self.format_number(stats['additions'])} -{self.format_number(stats['deletions'])} = {net:+,} net lines")
            
            # If stats seem low, warn user
            if self.stats['overall']['commits'] < 100:
                print("\n⚠️  Warning: Statistics seem low. This might be due to:")
                print("   - GitHub API rate limiting")
                print("   - Private repositories not accessible") 
                print("   - Recent commits not yet indexed")
            
            success = self.update_readme()
            
            if success:
                print("\n✅ Process completed successfully!")
                print("📝 README.md has been updated with latest statistics")
            else:
                print("\n❌ Failed to update README.md")
                
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    generator = GitHubStatsGenerator()
    generator.run()