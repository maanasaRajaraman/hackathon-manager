import textwrap

from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import Participant, Theme, Submission
import openai
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.db import models
import os
import google.generativeai as genai
import re

def themes(request):
    themes = Theme.objects.all()
    return render(request, 'themes.html', {'themes': themes})


def home(request):
    return render(request, 'home.html')


def register(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        skills = request.POST['skills']
        Participant.objects.create(name=name, email=email, skills=skills)
        return redirect('themes')
    return render(request, 'register.html')


def submit_project(request):
    if request.method == 'POST':
        team_name = request.POST['team_name']
        project_name = request.POST['project_name']
        github_link = request.POST['github_link']
        summary_details = request.FILES['summary_details']
        other_docs = request.FILES.get('other_docs')
        theme_id = request.POST['theme']
        theme = Theme.objects.get(id=theme_id)

        Submission.objects.create(
            team_name=team_name,
            project_name=project_name,
            github_link=github_link,
            summary_details=summary_details,
            other_docs=other_docs,
            theme=theme
        )

        return HttpResponse("""
            <script>
                alert('Submission saved');
                window.location.href='/';
            </script>
        """)

    themes = Theme.objects.all()
    return render(request, 'submit_project.html', {'themes': themes})


GEMINI_API_KEY = 'AIzaSyAcFpKQo3hk1Z2jdtYO4LNpoNVafVZxfmI'
genai.configure(api_key=(GEMINI_API_KEY))

def generate_feedback(summary_content):
    try:
        response = genai.generate_message(
            model="gemini-1.5-pro-latest",  # Replace with the appropriate model name
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides feedback for projects."},
                {"role": "user", "content": f"Provide detailed feedback for the following project summary:\n\n{summary_content}"}
            ],
            max_output_tokens=500
        )
        feedback = response['candidates'][0]['content']  # Extract feedback from the response
        return feedback
    except Exception as e:
        return f"Error generating feedback: {str(e)}"


def feedback_submission(request, submission_id):
    feedback = generate_feedback(submission_id)
    return render(request, 'submission_feedback.html', {'feedback': feedback})


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('/')  # Redirect non-admins to home page

    theme_counts = Theme.objects.annotate(count=models.Count('submission'))

    return render(request, 'admin_dashboard.html', {
        'theme_counts': theme_counts,
        'total_submissions': Submission.objects.count()
    })


def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')  # Redirect to admin dashboard on successful login
        else:
            return render(request, 'admin_login.html', {'error': 'Invalid credentials or not an admin user.'})
    return render(request, 'admin_login.html')


def submissions_page(request):
    submissions = Submission.objects.all()
    return render(request, 'submissions_page.html', {'submissions': submissions})


import google.generativeai as genai
from django.shortcuts import render, get_object_or_404
from .models import Submission

# Define the model globally to avoid re-instantiating it in every request
model = genai.GenerativeModel("gemini-1.5-pro-latest")

def generate_feedback_page(request):
    def format_text(text):
        # Convert '**' to bold (<b>...</b>)
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)

        # Convert '*' to bullets (<li>...</li>)
        text = re.sub(r"\*\s(.*?)(?=(\*\s|$))", r"<li>\1</li>", text)

        # Wrap bullets in a <ul> tag
        text = re.sub(r"(<li>.*?</li>)", r"<ul>\1</ul>", text, flags=re.DOTALL)

        return text
    def beautify_feedback(raw_feedback):
        # Split feedback into sections based on predefined keywords
        sections = {
            "Overview": [],
            "Strengths": [],
            "Weaknesses": [],
            "Suggestions for Improvement": [],
            "Example of a Revised Summary": []
        }

        # Determine the current section and append lines to it
        current_section = None
        for line in raw_feedback.splitlines():
            if "**Strengths:**" in line:
                current_section = "Strengths"
            elif "**Weaknesses:**" in line:
                current_section = "Weaknesses"
            elif "**Suggestions for Improvement:**" in line:
                current_section = "Suggestions for Improvement"
            elif "**Revised Summary Example" in line:
                current_section = "Example of a Revised Summary"
            elif "**Overview:**" in line:
                current_section = "Overview"
            elif current_section:
                sections[current_section].append(line)

        # Beautify each section
        beautified_feedback = []
        for section, content in sections.items():
            beautified_feedback.append(f"### {section}")
            for paragraph in content:
                paragraph = paragraph.strip()
                if paragraph.startswith("*"):
                    # Format as list items
                    beautified_feedback.append(f"- {paragraph[1:].strip()}")
                elif paragraph.startswith("```"):
                    # Handle code block formatting
                    beautified_feedback.append(paragraph)
                elif paragraph:
                    # Wrap and format normal text
                    wrapped = textwrap.fill(paragraph, width=80)
                    beautified_feedback.append(wrapped)

        return "\n\n".join(beautified_feedback)

    if request.method == "POST":
        submission_id = request.POST.get("submission_id")
        submission = get_object_or_404(Submission, id=submission_id)

        # Read the summary document content
        summary_path = submission.summary_details.path
        with open(summary_path, "r") as file:
            summary_content = file.read()

        # Generate feedback using Gemini API
        try:
            response = model.generate_content(
                f"Provide detailed feedback for the following project summary:\n\n{summary_content}",
                generation_config=genai.GenerationConfig(
                    response_mime_type="text/plain"  # Use "text/plain" for simple text responses
                ),
            )
            feedback = response.__getattribute__("_result").candidates[0].content.parts[0].text
            feedback = format_text(feedback)
        except Exception as e:
            feedback = f"Error generating feedback: {str(e)}"

        return render(request, "submission_feedback.html", {"feedback": feedback})

    # If GET, render the form
    teams = Submission.objects.all()
    return render(request, "generate_feedback_page.html", {"teams": teams})
