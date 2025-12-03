from django.core.management.base import BaseCommand
from achievements.models import Skill

class Command(BaseCommand):
    help = 'Populates the Skill table with a list of common technical skills'

    def handle(self, *args, **kwargs):
        skills_list = [
            # Programming Languages
            "Python", "Java", "JavaScript", "C++", "C#", "Ruby", "Go", "Swift", "Kotlin", "Rust", "PHP", "TypeScript",
            
            # Web Development
            "HTML", "CSS", "React", "Angular", "Vue.js", "Node.js", "Django", "Flask", "Spring Boot", "ASP.NET", "Laravel",
            
            # Data Science & AI
            "Machine Learning", "Deep Learning", "Data Analysis", "Data Visualization", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-learn", "NLP", "Computer Vision",
            
            # Database
            "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Oracle", "SQLite",
            
            # DevOps & Cloud
            "Docker", "Kubernetes", "AWS", "Azure", "Google Cloud", "CI/CD", "Git", "Linux", "Jenkins", "Terraform",
            
            # Mobile Development
            "Android", "iOS", "Flutter", "React Native",
            
            # Cybersecurity
            "Network Security", "Ethical Hacking", "Cryptography", "Penetration Testing",
            
            # Soft Skills (Optional, but good to have)
            "Leadership", "Communication", "Teamwork", "Problem Solving", "Time Management"
        ]

        count = 0
        for skill_name in skills_list:
            skill, created = Skill.objects.get_or_create(name=skill_name.lower().strip())
            if created:
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully added {count} new skills.'))
