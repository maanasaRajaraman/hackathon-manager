from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import Participant, Theme, Submission
import openai
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.db import models


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

# Add your own api key
openai.api_key = "your_api_key"


def generate_feedback(submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    file_content = submission.summary_details.read().decode('utf-8')

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for generating project feedback."},
            {"role": "user", "content": f"Provide constructive feedback for this project: {file_content}"}
        ]
    )
    feedback_text = response['choices'][0]['message']['content']
    return feedback_text


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


def generate_feedback_page(request):
    teams = Submission.objects.values('id', 'team_name')

    if request.method == 'POST':
        submission_id = request.POST['submission_id']
        feedback = generate_feedback(submission_id)

        return render(request, 'generate_feedback_page.html', {
            'teams': teams,
            'feedback': feedback
        })

    return render(request, 'generate_feedback_page.html', {'teams': teams})
