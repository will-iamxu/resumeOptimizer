import os
import openai
from flask import Flask, request, render_template, redirect, url_for, session, send_file, flash
from dotenv import load_dotenv
import subprocess
import tempfile
import io 
import shutil 
import uuid # For generating unique filenames
import re # For sanitizing filename

load_dotenv() 

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
openai.api_key = os.getenv("OPENAI_API_KEY")

DEFAULT_RESUME_PATH = "default_resume.tex"
TEMP_LATEX_DIR = "tmp_latex_files" # Directory to store temporary LaTeX files

# Ensure the temporary LaTeX directory exists
if not os.path.exists(TEMP_LATEX_DIR):
    os.makedirs(TEMP_LATEX_DIR)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        job_description = request.form['job_description']
        resume_latex = request.form['resume_latex']
        company_name = request.form.get('company_name', 'Company') # Get company name
        
        if not openai.api_key:
            flash("Error: OpenAI API key not configured. Please set it in a .env file.", "error")
            return redirect(url_for('index'))
        if not job_description or not resume_latex:
            flash("Error: Job description and resume LaTeX cannot be empty.", "error")
            return redirect(url_for('index'))

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
1. Carefully analyze the job description to identify key skills, experiences, qualifications, and **keywords** the employer is looking for.
2. Review the original LaTeX resume. Your primary goal is to **enhance and deeply elaborate on the existing sections and content**, strategically weaving in the identified keywords from the job description where relevant and natural.
3. Modify the LaTeX resume to highlight the candidate's most relevant qualifications and experiences.
    *   **Keyword Integration:** Naturally incorporate important keywords and phrases from the job description into the descriptions of experiences, projects, and skills.
    *   **Skills Section Enhancement:**
        *   Review the skills listed in the job description.
        *   If the original resume has a skills section, update it to include relevant skills from the job description that the candidate likely possesses based on their experience, even if not explicitly listed in the original resume's skills section.
        *   If the original resume does *not* have a dedicated skills section, but skills are clearly important for the job, consider adding a concise skills section populated with relevant skills from the job description and those evident from the candidate's experience.
    *   **Content Expansion:** Focus on making existing bullet points, project descriptions, and skill entries more detailed, specific, and impactful. For example, instead of just listing a skill, describe how it was used or what was achieved with it. Quantify achievements with numbers or specific outcomes whenever possible.
    *   **Page Utilization:** The aim is for the elaborated content to naturally fill the page or pages. If the original resume is sparse, expand significantly on each existing point to make it substantial. It's better to have fewer, well-detailed points than many brief ones. The resume can extend beyond one page if the depth of relevant information warrants it.
    *   **Section Management:**
        *   Prioritize improving the content within the sections already present in the original LaTeX resume.
        *   **Do NOT add an 'Objective' section if one was not present in the original resume.** If a professional introduction is beneficial and missing, consider a 'Summary' or 'Professional Profile' section, but only if it genuinely adds value beyond well-detailed experience and skills sections.
4. Ensure the output is a complete and valid LaTeX document. Maintain the original structure and document class (e.g., `article`, `resume`) as much as possible.
5. Do NOT add any comments, explanations, or markdown formatting outside of the LaTeX code. Only output the raw, modified LaTeX resume content.
6. The goal is a professional, well-formatted resume that effectively showcases the candidate's qualifications through detailed, specific, and keyword-rich descriptions.

Optimized LaTeX Resume:
"""
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an expert resume optimizer specializing in LaTeX resumes."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                )
                optimized_resume_latex = response.choices[0].message.content.strip()
            except AttributeError:
                response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an expert resume optimizer specializing in LaTeX resumes."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                )
                optimized_resume_latex = response.choices[0].message.content.strip()
            
            if optimized_resume_latex.startswith("```latex"):
                optimized_resume_latex = optimized_resume_latex[len("```latex"):].strip()
            if optimized_resume_latex.startswith("```"):
                optimized_resume_latex = optimized_resume_latex[len("```"):].strip()
            if optimized_resume_latex.endswith("```"):
                optimized_resume_latex = optimized_resume_latex[:-len("```")].strip()

            # Save optimized LaTeX to a temporary file server-side
            temp_filename = f"{uuid.uuid4()}.tex"
            temp_filepath = os.path.join(TEMP_LATEX_DIR, temp_filename)
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                f.write(optimized_resume_latex)
            
            session['optimized_resume_filename'] = temp_filename 
            session['company_name_for_pdf'] = company_name # Store company name in session
            # Pass the actual LaTeX content to the template for display, but not for session storage for download
            return render_template('result.html', optimized_resume=optimized_resume_latex) 
        
        except Exception as e:
            flash(f"An error occurred during optimization: {str(e)}", "error")
            return redirect(url_for('index'))
            
    # GET request
    default_resume_text = ""
    if os.path.exists(DEFAULT_RESUME_PATH):
        try:
            with open(DEFAULT_RESUME_PATH, 'r', encoding='utf-8') as f:
                default_resume_text = f.read()
        except Exception as e:
            flash(f"Error loading default resume: {str(e)}", "error")
            
    return render_template('index.html', default_resume_text=default_resume_text)

@app.route('/save_default_resume', methods=['POST'])
def save_default_resume():
    resume_data = request.form.get('resume_data')
    if resume_data is None:
        flash("No resume data received to save.", "error")
        return redirect(url_for('index'))
    try:
        with open(DEFAULT_RESUME_PATH, 'w', encoding='utf-8') as f:
            f.write(resume_data)
        flash("Default resume saved successfully!", "success")
    except Exception as e:
        flash(f"Error saving default resume: {str(e)}", "error")
    return redirect(url_for('index'))

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    optimized_resume_filename = session.get('optimized_resume_filename')
    company_name_for_pdf = session.get('company_name_for_pdf', 'Optimized') # Get company name from session

    if not optimized_resume_filename:
        flash('No optimized resume reference found in session. Please optimize first.', 'error')
        return redirect(url_for('index'))

    temp_latex_filepath = os.path.join(TEMP_LATEX_DIR, optimized_resume_filename)

    if not os.path.exists(temp_latex_filepath):
        flash('Optimized resume file not found on server. Please try optimizing again.', 'error')
        # Clean up session key if file is missing
        if 'optimized_resume_filename' in session:
            session.pop('optimized_resume_filename')
        return redirect(url_for('index'))

    try:
        with open(temp_latex_filepath, 'r', encoding='utf-8') as f:
            optimized_resume_latex = f.read()

        with tempfile.TemporaryDirectory() as tmpdir_compile: # Renamed to avoid conflict
            # The TeX file for compilation will be created inside this new temporary directory
            compile_tex_filename = "optimized_for_compile.tex" 
            compile_pdf_filename = "optimized_for_compile.pdf"
            compile_tex_filepath = os.path.join(tmpdir_compile, compile_tex_filename)
            
            with open(compile_tex_filepath, 'w', encoding='utf-8') as f:
                f.write(optimized_resume_latex)

            compilation_log = ""
            compilation_successful = False
            # PDF path will be inside tmpdir_compile
            pdf_output_path = os.path.join(tmpdir_compile, compile_pdf_filename)

            for i in range(2): # Run pdflatex twice
                process = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', '-output-directory', tmpdir_compile, compile_tex_filepath],
                    capture_output=True, text=True, encoding='utf-8', errors='ignore',
                    timeout=30 
                )
                compilation_log += f"--- pdflatex Run {i+1} ---\nReturn Code: {process.returncode}\nStdout:\n{process.stdout}\nStderr:\n{process.stderr}\n"
                
                if process.returncode == 0 and os.path.exists(pdf_output_path):
                    compilation_successful = True
                    if i == 1: break 
                else:
                    compilation_successful = False
                    break

            if compilation_successful:
                pdf_buffer = io.BytesIO()
                with open(pdf_output_path, 'rb') as f_pdf:
                    pdf_buffer.write(f_pdf.read())
                pdf_buffer.seek(0) 

                # Sanitize company name for filename
                safe_company_name = re.sub(r'[^\w\s-]', '', company_name_for_pdf).strip().replace(' ', '_')
                if not safe_company_name: # Handle case where company name becomes empty after sanitization
                    safe_company_name = "Resume"
                
                download_filename = f"{safe_company_name}_resume.pdf"

                return send_file(
                    pdf_buffer,
                    as_attachment=True,
                    download_name=download_filename,
                    mimetype='application/pdf'
                )
            else:
                log_filepath = compile_tex_filepath.replace(".tex", ".log")
                full_log_content = "Could not retrieve full .log file or it was empty."
                if os.path.exists(log_filepath):
                    try:
                        with open(log_filepath, "r", encoding="utf-8", errors="ignore") as log_f:
                            full_log_content = log_f.read()
                            if not full_log_content.strip():
                                full_log_content = "Log file was empty."
                            
                            # Extract missing package information
                            missing_packages = []
                            package_pattern = r"! LaTeX Error: File ['\"](.*?).sty['\"](.*?)not found"
                            for line in full_log_content.split('\n'):
                                package_match = re.search(package_pattern, line)
                                if package_match:
                                    missing_packages.append(package_match.group(1).replace('.sty', ''))
                            
                            if missing_packages:
                                missing_pkgs_str = ", ".join(missing_packages)
                                flash(f"Missing LaTeX packages detected: {missing_pkgs_str}. Please install these packages using MiKTeX Console.", "error")
                                
                                # Add instructions for installing packages
                                installation_instructions = (
                                    f"<div class='alert alert-info'>"
                                    f"<h4>Installing Missing LaTeX Packages</h4>"
                                    f"<p>To install the missing packages using MiKTeX Console:</p>"
                                    f"<ol>"
                                    f"<li>Open MiKTeX Console (search for it in your Start menu)</li>"
                                    f"<li>Go to the 'Packages' tab</li>"
                                    f"<li>Use the search box to find each package: {missing_pkgs_str}</li>"
                                    f"<li>Select each package and click the '+' button to install it</li>"
                                    f"</ol>"
                                    f"<p>Or enable 'Install missing packages on-the-fly':</p>"
                                    f"<ol>"
                                    f"<li>In MiKTeX Console, go to Settings → General</li>"
                                    f"<li>Set 'Install missing packages on-the-fly' to 'Yes'</li>"
                                    f"<li>Click 'Apply', then try downloading the PDF again</li>"
                                    f"</ol>"
                                    f"</div>"
                                )
                                flash(installation_instructions, "info_html")
                    except Exception as log_e:
                        full_log_content = f"Error reading log file: {str(log_e)}"
                
                error_message_html = (
                    "<p>LaTeX compilation failed. Please check the details below. "
                    "This often happens if the LaTeX code is invalid or missing required packages "
                    "that are not automatically installed by your LaTeX distribution.</p>"
                    f"<h3>Combined Stdout/Stderr from pdflatex runs:</h3><pre>{compilation_log}</pre>"
                    f"<h3>Full .log file content (if available, truncated):</h3><pre>{full_log_content[:10000]}</pre>"
                )
                flash(error_message_html, "error_html") 
                return error_message_html, 500

    except subprocess.TimeoutExpired:
        flash("LaTeX compilation timed out. The document might be too complex or there could be an issue with the LaTeX installation.", "error")
        return redirect(url_for('index')) 
    except FileNotFoundError: 
        flash("Error: pdflatex command not found. Ensure a LaTeX distribution is installed and pdflatex is in your system's PATH.", "error")
        return redirect(url_for('index')) 
    except Exception as e:
        flash(f"An unexpected error occurred during PDF generation: {str(e)}", "error")
        return redirect(url_for('index'))
    finally:
        # Clean up the temporary LaTeX file from TEMP_LATEX_DIR
        if os.path.exists(temp_latex_filepath):
            try:
                os.remove(temp_latex_filepath)
            except Exception as e_remove:
                print(f"Error removing temporary LaTeX file {temp_latex_filepath}: {e_remove}")
        # Clean up session key
        if 'optimized_resume_filename' in session:
            session.pop('optimized_resume_filename', None)
        if 'company_name_for_pdf' in session:
            session.pop('company_name_for_pdf', None)


if __name__ == '__main__':
    # Ensure the templates directory exists, Flask will look for templates here
    if not os.path.exists('templates'):
        os.makedirs('templates')
        print("Created 'templates' directory. Make sure your index.html and result.html are inside it.")
    
    app.run(debug=True)
