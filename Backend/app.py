from flask import Flask, request, jsonify, send_file
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS
import os
import traceback
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from io import BytesIO
import re
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Set up upload folder for document review
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Root endpoint
@app.route('/')
def home():
    return "Welcome to the Legal Document Assistant API!"

# Test endpoint
@app.route('/test', methods=['GET'])
def test():
    return "Backend is working!"

# Document generation endpoint
@app.route('/generate-doc', methods=['POST'])
def generate_doc():
    try:
        print("=== Document Generation Request Received ===")
        data = request.json
        print(f"Received data: {data}")
        
        # Enhanced validation with specific error messages
        validation_errors = []
        
        # Check parties
        if 'parties' not in data:
            validation_errors.append("Parties information is missing")
        elif len(data['parties']) < 2:
            validation_errors.append("Two parties are required")
        else:
            party1 = data['parties'][0].strip() if data['parties'][0] else ""
            party2 = data['parties'][1].strip() if data['parties'][1] else ""
            if not party1:
                validation_errors.append("Party 1 name cannot be empty")
            if not party2:
                validation_errors.append("Party 2 name cannot be empty")
        
        # Document type specific validation
        document_type = data.get('document_type', 'NDA')
        if document_type == 'NDA':
            if 'confidentiality_terms' not in data or not data.get('confidentiality_terms', '').strip():
                validation_errors.append("Confidentiality terms are required for NDAs")
        elif document_type == 'Employment Contract':
            employment_terms = data.get('employment_terms', {})
            if not employment_terms.get('position', '').strip():
                validation_errors.append("Position is required for Employment Contracts")
            if not employment_terms.get('salary', '').strip():
                validation_errors.append("Salary information is required for Employment Contracts")
        elif document_type == 'Service Agreement':
            service_terms = data.get('service_terms', {})
            if not service_terms.get('serviceDescription', '').strip():
                validation_errors.append("Service description is required for Service Agreements")
        
        if validation_errors:
            print(f"Validation errors: {validation_errors}")
            return jsonify({"error": "Validation failed", "details": validation_errors}), 400
            
        # If validation passes, continue with document generation
        party1 = data['parties'][0].strip()
        party2 = data['parties'][1].strip()

        # Build the base prompt with common fields
        prompt = f"""
        Generate a professional {document_type} between {party1} and {party2}.
        
        Jurisdiction: {data.get('jurisdiction', 'Not specified')}.
        Duration: {data.get('duration', 'Indefinite')}.
        """

        # Add document-specific details to the prompt
        if document_type == 'NDA':
            prompt += f"Confidentiality Terms: {data.get('confidentiality_terms', 'None')}.\n"
        
        elif document_type == 'Employment Contract':
            employment_terms = data.get('employment_terms', {})
            prompt += f"""
            Position: {employment_terms.get('position', 'Not specified')}.
            Salary: {employment_terms.get('salary', 'Not specified')}.
            Start Date: {employment_terms.get('startDate', 'Not specified')}.
            Probation Period: {employment_terms.get('probationPeriod', 'Not specified')}.
            """
        
        elif document_type == 'Service Agreement':
            service_terms = data.get('service_terms', {})
            prompt += f"""
            Service Description: {service_terms.get('serviceDescription', 'Not specified')}.
            Deliverables: {service_terms.get('deliverables', 'Not specified')}.
            Payment Terms: {service_terms.get('paymentTerms', 'Not specified')}.
            """

        # Add any additional clauses
        if 'clauses' in data and data['clauses']:
            prompt += f"Additional Clauses: {', '.join(data['clauses'])}.\n"

        # Add instructions for formatting the document
        prompt += """
        Format the document professionally with numbered sections and clauses.
        Include appropriate legal language, definitions, and standard clauses for this type of document.
        Include signature blocks at the end for all parties.
        """

        print("Calling OpenAI API for document generation...")
        
        # Call OpenAI API with appropriate settings based on document complexity
        max_tokens = 800  # Default
        if document_type in ['Employment Contract', 'Service Agreement']:
            max_tokens = 1200  # More complex documents need more tokens
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7  # Slightly more creative but still formal
            )
            
            generated_doc = response.choices[0].message.content
            print(f"Document generated successfully, length: {len(generated_doc)} characters")
            return jsonify({"message": "Document generated!", "document": generated_doc})
            
        except Exception as api_error:
            print(f"OpenAI API error: {str(api_error)}")
            return jsonify({"error": f"Error generating document with AI: {str(api_error)}"}), 500

    except Exception as e:
        print(f"Error in generate_doc: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Document review endpoint
@app.route('/review-doc', methods=['POST'])
def review_doc():
    try:
        print("=== Document Review Request Received ===")
        print(f"Form keys: {list(request.form.keys())}")
        print(f"Files keys: {list(request.files.keys())}")
        
        focus_area = request.form.get('focus_area', 'general')
        print(f"Focus area: {focus_area}")
        
        document_text = ""
        
        # Handle file upload
        if 'document' in request.files:
            file = request.files['document']
            print(f"File received: {file.filename}, type: {file.content_type}, size: {file.content_length if hasattr(file, 'content_length') else 'unknown'}")
            
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                print(f"Saving file to: {file_path}")
                
                try:
                    file.save(file_path)
                    print(f"File saved successfully")
                    
                    # For text files, read directly
                    if filename.endswith('.txt'):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                document_text = f.read()
                            print(f"Read {len(document_text)} characters from text file")
                        except UnicodeDecodeError:
                            # Try another encoding if UTF-8 fails
                            with open(file_path, 'r', encoding='latin-1') as f:
                                document_text = f.read()
                            print(f"Read {len(document_text)} characters using latin-1 encoding")
                    else:
                        # For non-text files, we'd normally need additional libraries to extract text
                        # For now, just use a placeholder message
                        document_text = f"Content extracted from {filename}"
                        print("Using placeholder text for non-txt file")
                except Exception as file_error:
                    print(f"Error saving or processing file: {str(file_error)}")
                    return jsonify({"error": f"Error processing file: {str(file_error)}"}), 500
            else:
                print("Empty filename received")
        
        # Handle text input
        elif 'document_text' in request.form:
            document_text = request.form.get('document_text')
            print(f"Received document_text with {len(document_text)} characters")
        else:
            print("No document or document_text found in request")
        
        if not document_text:
            print("No document content provided")
            return jsonify({"error": "No document content provided"}), 400
        
        # Check if document is too long
        if len(document_text) > 100000:  # Limit to ~100KB of text
            return jsonify({"error": "Document is too large. Please upload a smaller document."}), 400
        
        # Build prompt based on focus area
        focus_instructions = {
            'general': "Provide a general review of the document's structure, completeness, and effectiveness.",
            'clarity': "Focus on language clarity, readability, and potential ambiguities.",
            'completeness': "Assess whether the document has all necessary clauses and protections.",
            'risks': "Identify potential risks, loopholes, or vulnerabilities in the agreement.",
            'compliance': "Evaluate the document's compliance with common legal requirements."
        }
        
        instruction = focus_instructions.get(focus_area, focus_instructions['general'])
        print(f"Using instruction for focus area '{focus_area}': {instruction}")
        
        prompt = f"""
        Please review the following legal document and provide:
        1. A brief summary of the document (2-3 sentences)
        2. Specific suggestions for improvement (3-5 points)
        3. Potential issues or risks with severity ratings (high, medium, low)
        
        {instruction}
        
        Document:
        {document_text}
        """
        
        print("Calling OpenAI API for document review...")
        
        try:
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
                temperature=0.5  # Lower temperature for more consistent analysis
            )
            
            ai_response = response.choices[0].message.content
            print("Received response from OpenAI")
            
            # For now, we'll use a simple approach with predefined structure
            # In a production app, you would implement proper parsing of the AI response
            analysis = {
                "summary": "This document has been analyzed based on your selected focus area.",
                "suggestions": [
                    {"type": "Clarity", "text": "Consider simplifying the language in legal terms sections."},
                    {"type": "Completeness", "text": "Add more specific details about termination conditions."},
                    {"type": "Structure", "text": "Reorganize sections to follow standard legal document format."}
                ],
                "issues": [
                    {"severity": "high", "title": "Missing Clause", "description": "The agreement may lack a clear dispute resolution mechanism."},
                    {"severity": "medium", "title": "Ambiguous Terms", "description": "Some provisions may contain potentially ambiguous language."},
                    {"severity": "low", "title": "Minor Formatting", "description": "There may be inconsistent formatting throughout the document."}
                ],
                "improvements": ai_response
            }
            
            print("Returning analysis to client")
            return jsonify(analysis)
            
        except Exception as api_error:
            print(f"OpenAI API error: {str(api_error)}")
            return jsonify({"error": f"Error analyzing document with AI: {str(api_error)}"}), 500
    
    except Exception as e:
        print(f"Error in document review: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# PDF Generation endpoint
@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        print("=== PDF Generation Request Received ===")
        data = request.json
        document_text = data.get('document_text', '')
        document_type = data.get('document_type', 'Legal Document')
        
        print(f"Generating PDF for {document_type}, content length: {len(document_text)} characters")
        
        if not document_text:
            return jsonify({"error": "No document content provided"}), 400
        
        # Create a BytesIO buffer to receive PDF data
        buffer = BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,  # 1 inch margins
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1,  # Center
            spaceAfter=24
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceBefore=6,
            spaceAfter=6
        )
        
        # Add document header with date
        current_date = datetime.now().strftime("%B %d, %Y")
        elements.append(Paragraph(f"{document_type}", title_style))
        elements.append(Paragraph(f"Generated on: {current_date}", normal_style))
        elements.append(Spacer(1, 24))
        
        # Process document text - look for sections, paragraphs, etc.
        # Simple approach: split by lines and process each
        section_pattern = re.compile(r'^(\d+\.|\d+\)|\d+\s|\*\s|[A-Z][A-Z\s]+:)')
        
        lines = document_text.split('\n')
        for line in lines:
            if not line.strip():
                continue
                
            # Check if this looks like a section heading
            if section_pattern.match(line.strip()):
                elements.append(Paragraph(line.strip(), heading_style))
            else:
                elements.append(Paragraph(line.strip(), normal_style))
        
        # Add space for signatures
        elements.append(Spacer(1, 36))
        elements.append(Paragraph("SIGNATURES", heading_style))
        
        # Create signature lines
        date_now = datetime.now().strftime("%B %d, %Y")
        sig_data = [
            ['___________________________', '___________________________'],
            ['Signature', 'Signature'],
            ['', ''],
            ['___________________________', '___________________________'],
            ['Printed Name', 'Printed Name'],
            ['', ''],
            ['___________________________', '___________________________'],
            ['Date', 'Date'],
        ]
        
        sig_table = Table(sig_data, colWidths=[2.5*inch, 2.5*inch])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(sig_table)
        
        # Build the PDF
        try:
            doc.build(elements)
            print("PDF generated successfully")
        except Exception as build_error:
            print(f"Error building PDF: {str(build_error)}")
            traceback.print_exc()
            return jsonify({"error": f"Error building PDF: {str(build_error)}"}), 500
        
        # Move to the beginning of the buffer
        buffer.seek(0)
        
        # Return the PDF as an attachment
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{document_type.replace(' ', '_')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)