import os
import openai
from flask import Flask, request, render_template, redirect, url_for
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        job_description = request.form['job_description']
        resume_latex = request.form['resume_latex']
        
        if not openai.api_key:
            return "Error: OpenAI API key not configured. Please set it in a .env file.", 500
        if not job_description or not resume_latex:
            return "Error: Job description and resume LaTeX cannot be empty.", 400

        try:
            prompt = f"""
You are an expert resume optimizer. Your task is to tailor the provided LaTeX resume to a specific job description.

Job Description:
---
{job_description}
---

Original LaTeX Resume:
---
{resume_latex}
---

Instructions:
1. Carefully analyze the job description to identify key skills, experiences, qualifications, and keywords the employer is looking for.
2. Review the original LaTeX resume and identify areas that can be improved or rephrased to better match the job description.
3. Modify the LaTeX resume to highlight the candidate's most relevant qualifications and experiences for this specific role.
4. Ensure the output is a complete and valid LaTeX document, maintaining the original structure as much as possible, but making necessary content changes.
5. Focus on rephrasing bullet points, a summary/objective if present, and potentially reordering sections if it significantly improves alignment. Be cautious with major structural changes unless absolutely necessary.
6. Do NOT add any comments, explanations, or markdown formatting outside of the LaTeX code. Only output the raw, modified LaTeX resume content.

Optimized LaTeX Resume:
"""
            
            response = openai.chat.completions.create(
                model="gpt-4o", # Or use "gpt-4" if you have access and prefer it
                messages=[
                    {"role": "system", "content": "You are an expert resume optimizer specializing in LaTeX resumes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5, # Adjust for creativity vs. precision
            )
            
            optimized_resume_latex = response.choices[0].message.content.strip()
            
            # Sometimes the model might still wrap the output in ```latex ... ```
            if optimized_resume_latex.startswith("```latex"):
                optimized_resume_latex = optimized_resume_latex[len("```latex"):].strip()
            if optimized_resume_latex.startswith("```"): # General backticks
                optimized_resume_latex = optimized_resume_latex[len("```"):].strip()
            if optimized_resume_latex.endswith("```"):
                optimized_resume_latex = optimized_resume_latex[:-len("```")].strip()

            return render_template('result.html', optimized_resume=optimized_resume_latex)
        
        except Exception as e:
            return f"An error occurred: {str(e)}", 500
            
    return render_template('index.html')

if __name__ == '__main__':
    # Ensure the templates directory exists, Flask will look for templates here
    if not os.path.exists('templates'):
        os.makedirs('templates')
        print("Created 'templates' directory. Make sure your index.html and result.html are inside it.")
    
    app.run(debug=True)
