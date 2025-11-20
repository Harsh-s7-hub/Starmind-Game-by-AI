# utils/export_utils.py
"""
Export utilities for CSV, GIF, and PDF generation
"""

import csv
import time
import os
from typing import List, Dict


class ExportManager:
    """Manages exporting simulation data and recordings"""
    
    def __init__(self):
        self.output_dir = "exports"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def export_schedule_csv(self, flights: List, assignments: Dict, filename=None):
        """Export flight schedule to CSV"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"schedule_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['flight_id', 'type', 'priority', 'runway', 'gate', 'slot', 'fuel', 'emergency']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for flight in flights:
                row = {
                    'flight_id': flight.id,
                    'type': flight.type,
                    'priority': f"{flight.priority:.3f}",
                    'fuel': flight.fuel,
                    'emergency': 'Yes' if flight.emergency else 'No'
                }
                
                if flight.id in assignments:
                    runway, gate, slot = assignments[flight.id]
                    row['runway'] = runway
                    row['gate'] = gate
                    row['slot'] = slot
                else:
                    row['runway'] = 'N/A'
                    row['gate'] = 'N/A'
                    row['slot'] = 'N/A'
                
                writer.writerow(row)
        
        return filepath
    
    def export_kpi_summary_csv(self, kpis: Dict, filename=None):
        """Export KPI summary to CSV"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"kpis_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Metric', 'Value'])
            
            for key, value in kpis.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        writer.writerow([f"{key}_{subkey}", subvalue])
                else:
                    writer.writerow([key, value])
        
        return filepath
    
    def start_gif_recording(self, canvas_widget):
        """
        Start recording canvas to GIF
        Requires: pip install pillow
        """
        try:
            from PIL import Image, ImageGrab
            
            self.recording = True
            self.gif_frames = []
            self.canvas_widget = canvas_widget
            
            self._capture_frame()
            return True
            
        except ImportError:
            print("PIL/Pillow required for GIF recording")
            return False
    
    def _capture_frame(self):
        """Capture current canvas frame"""
        if not self.recording:
            return
        
        try:
            from PIL import Image, ImageGrab
            
            # Get canvas position
            x = self.canvas_widget.winfo_rootx()
            y = self.canvas_widget.winfo_rooty()
            w = self.canvas_widget.winfo_width()
            h = self.canvas_widget.winfo_height()
            
            # Capture region
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            self.gif_frames.append(img)
            
            # Schedule next frame (30fps = ~33ms)
            if self.recording:
                self.canvas_widget.after(100, self._capture_frame)
                
        except Exception as e:
            print(f"Frame capture error: {e}")
    
    def stop_gif_recording(self, filename=None):
        """Stop recording and save GIF"""
        self.recording = False
        
        if not self.gif_frames:
            print("No frames captured")
            return None
        
        try:
            from PIL import Image
            
            if filename is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"simulation_{timestamp}.gif"
            
            filepath = os.path.join(self.output_dir, filename)
            
            # Save as GIF
            self.gif_frames[0].save(
                filepath,
                save_all=True,
                append_images=self.gif_frames[1:],
                duration=100,  # 100ms per frame
                loop=0
            )
            
            print(f"Saved GIF with {len(self.gif_frames)} frames to {filepath}")
            self.gif_frames = []
            
            return filepath
            
        except Exception as e:
            print(f"GIF save error: {e}")
            return None
    
    def export_pdf_summary(self, flights: List, kpis: Dict, assignments: Dict, filename=None):
        """
        Export PDF summary report
        Requires: pip install reportlab
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            if filename is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"summary_{timestamp}.pdf"
            
            filepath = os.path.join(self.output_dir, filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title = Paragraph("IAATCMS Simulation Summary", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Timestamp
            timestamp_text = f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            story.append(Paragraph(timestamp_text, styles['Normal']))
            story.append(Spacer(1, 12))
            
            # KPI Table
            story.append(Paragraph("Key Performance Indicators", styles['Heading2']))
            story.append(Spacer(1, 6))
            
            kpi_data = [['Metric', 'Value']]
            for key, value in kpis.items():
                if not isinstance(value, dict):
                    kpi_data.append([key, str(value)])
            
            kpi_table = Table(kpi_data)
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(kpi_table)
            story.append(Spacer(1, 12))
            
            # Flight Schedule Table
            story.append(Paragraph("Flight Schedule", styles['Heading2']))
            story.append(Spacer(1, 6))
            
            schedule_data = [['Flight ID', 'Type', 'Priority', 'Runway', 'Gate', 'Emergency']]
            for flight in flights[:20]:  # Limit to 20 flights
                runway, gate = 'N/A', 'N/A'
                if flight.id in assignments:
                    r, g, s = assignments[flight.id]
                    runway, gate = r, g
                
                schedule_data.append([
                    flight.id,
                    flight.type,
                    f"{flight.priority:.2f}",
                    runway,
                    gate,
                    'Yes' if flight.emergency else 'No'
                ])
            
            schedule_table = Table(schedule_data)
            schedule_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(schedule_table)
            
            # Build PDF
            doc.build(story)
            
            return filepath
            
        except ImportError:
            print("reportlab required for PDF export")
            return None
        except Exception as e:
            print(f"PDF export error: {e}")
            return None


# Quick access functions

def quick_export_schedule(flights, assignments):
    """Quick export schedule to CSV"""
    exporter = ExportManager()
    return exporter.export_schedule_csv(flights, assignments)


def quick_export_kpis(kpis):
    """Quick export KPIs to CSV"""
    exporter = ExportManager()
    return exporter.export_kpi_summary_csv(kpis)
