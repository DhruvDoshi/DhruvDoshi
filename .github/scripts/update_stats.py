#!/usr/bin/env python3
"""
GitHub Coding Statistics Generator
Analyzes commit history and generates coding statistics for README
"""

import os
import json
import requests
from datetime import datetime, timedelta
import re
from collections import defaultdict

class GitHubStatsGenerator:
    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN')
        self.username = os.environ.get('GITHUB_USERNAME')
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.stats = {
            'today': {'additions': 0, 'deletions': 0, 'commits': 0},
            'week': {'additions': 0, 'deletions': 0, 'commits': 0},
            'month': {'additions': 0, 'deletions': 0, 'commits': 0},
            'year': {'additions': 0, 'deletions': 0, 'commits': 0},
            'overall': {'additions': 0, 'deletions': 0, 'commits': 0}
        }
    
    def get_repositories(self):
        """Get all repositories for the user including organizations"""
        repos = []
        page = 1
        
        while True:
            # Get user repos
            url = f'https://api.github.com/user/repos?page={page}&per_page=100&sort=updated'
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"Error fetching repos: {response.status_code}")
                break
                
            page_repos = response.json()
            if not page_repos:
                break
                
            repos.extend(page_repos)
            page += 1
        
        # Filter repos where user has pushed commits
        return [repo for repo in repos if not repo['fork'] or self.has_contributions(repo)]
    
    def has_contributions(self, repo):
        """Check if user has contributions to this repo"""
        url = f"https://api.github.com/repos/{repo['full_name']}/stats/contributors"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            contributors = response.json()
            if contributors:
                return any(contrib['author']['login'] == self.username for contrib in contributors)
        return False
    
    def get_commits_for_repo(self, repo_name):
        """Get commits for a specific repository"""
        commits = []
        page = 1
        since_date = (datetime.now() - timedelta(days=365)).isoformat()
        
        while True:
            url = f'https://api.github.com/repos/{repo_name}/commits'
            params = {
                'author': self.username,
                'since': since_date,
                'page': page,
                'per_page': 100
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                break
                
            page_commits = response.json()
            if not page_commits:
                break
                
            commits.extend(page_commits)
            page += 1
            
            # Limit to avoid rate limiting
            if len(commits) > 1000:
                break
        
        return commits
    
    def get_commit_stats(self, repo_name, commit_sha):
        """Get detailed stats for a specific commit"""
        url = f'https://api.github.com/repos/{repo_name}/commits/{commit_sha}'
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            commit_data = response.json()
            stats = commit_data.get('stats', {})
            return {
                'additions': stats.get('additions', 0),
                'deletions': stats.get('deletions', 0),
                'total': stats.get('total', 0)
            }
        return {'additions': 0, 'deletions': 0, 'total': 0}
    
    def categorize_by_time(self, commit_date):
        """Determine which time categories this commit falls into"""
        commit_dt = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
        now = datetime.now().replace(tzinfo=commit_dt.tzinfo)
        
        categories = []
        
        # Today (last 24 hours)
        if (now - commit_dt).days == 0:
            categories.append('today')
        
        # This week (last 7 days)
        if (now - commit_dt).days < 7:
            categories.append('week')
        
        # This month (last 30 days)
        if (now - commit_dt).days < 30:
            categories.append('month')
        
        # This year (last 365 days)
        if (now - commit_dt).days < 365:
            categories.append('year')
        
        # Overall (always true for processed commits)
        categories.append('overall')
        
        return categories
    
    def analyze_repositories(self):
        """Analyze all repositories and gather statistics"""
        print(f"Analyzing repositories for {self.username}...")
        
        repos = self.get_repositories()
        print(f"Found {len(repos)} repositories to analyze")
        
        for repo in repos[:20]:  # Limit to prevent rate limiting
            print(f"Analyzing {repo['full_name']}...")
            
            commits = self.get_commits_for_repo(repo['full_name'])
            print(f"Found {len(commits)} commits in {repo['name']}")
            
            for commit in commits:
                commit_date = commit['commit']['author']['date']
                categories = self.categorize_by_time(commit_date)
                
                # Get detailed commit stats
                commit_stats = self.get_commit_stats(repo['full_name'], commit['sha'])
                
                # Update stats for each applicable time period
                for category in categories:
                    self.stats[category]['additions'] += commit_stats['additions']
                    self.stats[category]['deletions'] += commit_stats['deletions']
                    self.stats[category]['commits'] += 1
    
    def generate_stats_table(self):
        """Generate markdown table with statistics"""
        table = """## Coding Statistics 📊

| Period | Lines Added | Lines Removed | Net Lines | Commits |
|--------|-------------|---------------|-----------|---------|"""
        
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
            
            table += f"\n| {label} | {stats['additions']:,} | {stats['deletions']:,} | {net_sign}{net_lines:,} | {stats['commits']:,} |"
        
        table += f"\n\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"
        
        return table
    
    def update_readme(self):
        """Update README.md with new statistics"""
        readme_path = 'README.md'
        
        if not os.path.exists(readme_path):
            print("README.md not found!")
            return
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Generate new stats table
        new_stats = self.generate_stats_table()
        
        # Find and replace existing stats section or add new one
        stats_pattern = r'## Coding Statistics 📊.*?(?=\n##|\n\[|$)'
        
        if re.search(stats_pattern, content, re.DOTALL):
            # Replace existing stats
            content = re.sub(stats_pattern, new_stats.rstrip(), content, flags=re.DOTALL)
        else:
            # Add stats after Github Languages and Status section
            github_stats_pattern = r'(## Github Languages and Status.*?</p>)'
            if re.search(github_stats_pattern, content, re.DOTALL):
                content = re.sub(
                    github_stats_pattern, 
                    r'\1\n\n' + new_stats, 
                    content, 
                    flags=re.DOTALL
                )
            else:
                # Add at the end before blog posts
                blog_pattern = r'(## Top Blog Posts)'
                content = re.sub(blog_pattern, new_stats + r'\n\1', content)
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("README.md updated successfully!")
    
    def run(self):
        """Main execution method"""
        if not self.token or not self.username:
            print("Error: GITHUB_TOKEN and GITHUB_USERNAME environment variables required")
            return
        
        try:
            self.analyze_repositories()
            self.update_readme()
            
            print("\nFinal Statistics:")
            for period, stats in self.stats.items():
                print(f"{period.capitalize()}: {stats['commits']} commits, "
                      f"+{stats['additions']} -{stats['deletions']} lines")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    generator = GitHubStatsGenerator()
    generator.run()