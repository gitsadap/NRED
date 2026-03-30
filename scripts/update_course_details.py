
import asyncio
from sqlalchemy import select, update
from app.database import SessionLocal
from app.models import Page

# Data for each course
courses = {
    "bachelor-nre": {
        "title": "วท.บ. ทรัพยากรธรรมชาติและสิ่งแวดล้อม",
        "subtitle": "B.Sc. Natural Resources and Environment",
        "philosophy": "ผลิตบัณฑิตที่มีความรู้คู่คุณธรรม นำภูมิปัญญาพัฒนาทรัพยากรและสิ่งแวดล้อมอย่างยั่งยืน",
        "credits": "142",
        "duration": "4",
        "tuition": "12,000",
        "careers": [
            "นักวิชาการสิ่งแวดล้อม (Environmentalist)", 
            "เจ้าหน้าที่ป่าไม้ (Forestry Officer)", 
            "นักประเมินผลกระทบสิ่งแวดล้อม (EIA Specialist)",
            "เจ้าหน้าที่ CSR ในองค์กรเอกชน"
        ],
        "iframe_src": "https://ww2.agi.nu.ac.th/th/?page_id=2885"
    },
    "bachelor-geo": {
        "title": "วท.บ. ภูมิศาสตร์",
        "subtitle": "B.Sc. Geography",
        "philosophy": "สร้างบัณฑิตภูมิศาสตร์ที่ทันสมัย ใส่ใจพื้นที่ มีทักษะเทคโนโลยี ภูมิใจในท้องถิ่น สู่สากล",
        "credits": "138",
        "duration": "4",
        "tuition": "12,000",
        "careers": [
            "นักภูมิศาสตร์และภูมิสารสนเทศ", 
            "เจ้าหน้าที่ GIS และรังวัด", 
            "นักผังเมือง", 
            "นักวิเคราะห์ข้อมูลพื้นที่"
        ],
        "iframe_src": "https://ww2.agi.nu.ac.th/th/?page_id=2883"
    },
    "master-nre": {
        "title": "วท.ม. ทรัพยากรธรรมชาติและสิ่งแวดล้อม",
        "subtitle": "M.Sc. Natural Resources and Environment",
        "philosophy": "มุ่งสร้างนักวิจัยและผู้บริหารทรัพยากรระดับสูง ที่มีความเป็นเลิศทางวิชาการและจริยธรรม",
        "credits": "36",
        "duration": "2",
        "tuition": "25,000",
        "careers": [
            "อาจารย์และนักวิจัย", 
            "ที่ปรึกษาด้านสิ่งแวดล้อม", 
            "ผู้บริหารจัดการโครงการทรัพยากร"
        ],
        "pdf_url": "https://ww2.agi.nu.ac.th/th/wp-content/uploads/2021/02/M.Sc_.NRE60.pdf"
    },
    "master-geo": {
        "title": "วท.ม. ภูมิศาสตร์",
        "subtitle": "M.Sc. Geography",
        "philosophy": "บูรณาการศาสตร์ภูมิศาสตร์เพื่อการจัดการพื้นที่และภัยพิบัติอย่างมีประสิทธิภาพ",
        "credits": "36",
        "duration": "2",
        "tuition": "25,000",
        "careers": [
            "ผู้เชี่ยวชาญด้าน GIS ขั้นสูง", 
            "นักวิจัยด้านภัยพิบัติและอุตุนิยมวิทยา", 
            "นักวางแผนนโยบายสาธารณะ"
        ],
        "pdf_url": "https://ww2.agi.nu.ac.th/th/wp-content/uploads/2023/06/M.Sc_.GEO65.pdf"
    },
    "master-env-sci": {
        "title": "วท.ม. วิทยาศาสตร์สิ่งแวดล้อม",
        "subtitle": "M.Sc. Environmental Science",
        "philosophy": "สร้างองค์ความรู้และนวัตกรรมด้านวิทยาศาสตร์สิ่งแวดล้อม เพื่อคุณภาพชีวิตที่ดีกว่า",
        "credits": "36",
        "duration": "2",
        "tuition": "25,000",
        "careers": [
            "นักวิทยาศาสตร์สิ่งแวดล้อม", 
            "ผู้เชี่ยวชาญด้านมลพิษและการบำบัด", 
            "นักวิจัย R&D ด้านสิ่งแวดล้อม"
        ],
        "pdf_url": "https://ww2.agi.nu.ac.th/th/wp-content/uploads/2023/07/M.Sc_.EnvSci66.pdf"
    },
    "phd-nre": {
        "title": "ปร.ด. ทรัพยากรธรรมชาติและสิ่งแวดล้อม",
        "subtitle": "Ph.D. Natural Resources and Environment",
        "philosophy": "ผู้นำทางปัญญาและการวิจัยขั้นสูง เพื่อการอนุรักษ์ทรัพยากรระดับนานาชาติ",
        "credits": "48",
        "duration": "3",
        "tuition": "40,000",
        "careers": [
            "นักวิชาการระดับเชี่ยวชาญ", 
            "ผู้บริหารระดับสูงองค์กรด้านสิ่งแวดล้อม", 
            "นักวิจัยอิสระระดับนานาชาติ"
        ],
        "pdf_url": "https://ww2.agi.nu.ac.th/th/wp-content/uploads/2017/12/Ph.D.NRE60.pdf"
    },
    "phd-env-sci": {
        "title": "ปร.ด. วิทยาศาสตร์สิ่งแวดล้อม",
        "subtitle": "Ph.D. Environmental Science",
        "philosophy": "สร้างนวัตกรและนักวิจัยระดับโลก เพื่อแก้ไขปัญหาวิกฤตสิ่งแวดล้อมโลก",
        "credits": "48",
        "duration": "3",
        "tuition": "40,000",
        "careers": [
            "นักวิจัยและพัฒนาเทคโนโลยีสิ่งแวดล้อม", 
            "ที่ปรึกษาระดับนานาชาติ", 
            "อาจารย์มหาวิทยาลัยชั้นนำ"
        ],
        "pdf_url": "https://ww2.agi.nu.ac.th/th/wp-content/uploads/2022/02/Ph.D.EnvSci60.pdf"
    }
}

def generate_html(data):
    # Determine bottom section (iframe or PDF embed)
    bottom_content = ""
    if "iframe_src" in data:
         # Bachelor -> use original link page inside iframe or button? 
         # The requirement says "Link to original PDF" usually. 
         # But for Bachelor we have web URL.
         bottom_content = f"""
            <div class="mt-8">
                <h3 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-600 to-blue-600 mb-6">โครงสร้างหลักสูตร (Curriculum Structure)</h3>
                <div class="aspect-w-16 aspect-h-9 h-[600px] border rounded-xl overflow-hidden shadow-sm">
                   <iframe src="{data['iframe_src']}" class="w-full h-full" style="border:none;"></iframe>
                </div>
                <div class="mt-4 text-center">
                    <a href="{data['iframe_src']}" target="_blank" class="inline-flex items-center px-6 py-3 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 transition">
                        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                        ดูรายละเอียดฉบับเต็ม
                    </a>
                </div>
            </div>
         """
    elif "pdf_url" in data:
         bottom_content = f"""
            <div class="mt-8">
                <h3 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-600 to-blue-600 mb-6">เอกสารหลักสูตร (Curriculum Document)</h3>
                <div class="aspect-w-16 aspect-h-9 h-[800px] border rounded-xl overflow-hidden shadow-sm bg-gray-100">
                   <iframe src="{data['pdf_url']}" class="w-full h-full" style="border:none;"></iframe>
                </div>
                <div class="mt-4 text-center">
                    <a href="{data['pdf_url']}" target="_blank" class="inline-flex items-center px-6 py-3 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition">
                        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                        ดาวน์โหลด PDF
                    </a>
                </div>
            </div>
         """

    career_html = "".join([f'<li class="flex items-start"><svg class="w-5 h-5 text-green-500 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg><span>{c}</span></li>' for c in data['careers']])

    template = f"""
    <div class="bg-gradient-to-b from-gray-50 to-white min-h-screen pb-16">
        <!-- Hero Header -->
        <div class="relative bg-teal-900 text-white py-24 overflow-hidden">
             <div class="absolute inset-0 bg-[url('/assets/images/hero-bg-2.jpg')] bg-cover bg-center opacity-10"></div>
             <div class="container mx-auto px-4 relative z-10 text-center">
                 <h1 class="text-3xl md:text-5xl font-bold mb-4" data-aos="fade-up">{data['title']}</h1>
                 <p class="text-xl md:text-2xl text-teal-100 font-light" data-aos="fade-up" data-aos-delay="100">{data['subtitle']}</p>
             </div>
        </div>

        <div class="container mx-auto px-4 -mt-10 relative z-20">
            <div class="bg-white rounded-2xl shadow-xl p-8 md:p-12">
                
                <!-- Philosophy Quote -->
                <div class="mb-12 text-center max-w-4xl mx-auto">
                    <svg class="w-12 h-12 text-teal-200 mx-auto mb-4" fill="currentColor" viewBox="0 0 24 24"><path d="M14.017 21L14.017 18C14.017 16.8954 13.1216 16 12.017 16H9C9.00001 7.29119 14.8696 2.61201 14.9818 2.52835L13.1818 0.125C13.0645 0.218 6 5.864 6 16C6 18.7614 8.23858 21 11 21H14.017ZM19 16C19 18.7614 21.2386 21 24 21H27.017L27.017 18C27.017 16.8954 26.1216 16 25.017 16H22C22 7.29119 27.8696 2.61201 27.9818 2.52835L26.1818 0.125C26.0645 0.218 19 5.864 19 16Z"></path></svg>
                    <p class="text-xl md:text-2xl font-serif italic text-gray-700 leading-relaxed">"{data['philosophy']}"</p>
                    <p class="text-sm text-gray-400 mt-4 uppercase tracking-widest font-bold">ปรัชญาหลักสูตร (Philosophy)</p>
                </div>

                <!-- Stats Grid -->
                <div class="grid md:grid-cols-3 gap-8 mb-16">
                    <div class="bg-teal-50 rounded-xl p-6 text-center border border-teal-100 hover:shadow-lg transition">
                        <div class="inline-flex items-center justify-center w-12 h-12 bg-teal-100 text-teal-600 rounded-full mb-4">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                        </div>
                        <h3 class="text-3xl font-bold text-teal-800">{data['credits']}</h3>
                        <p class="text-gray-600">หน่วยกิต (Credits)</p>
                    </div>
                    <div class="bg-blue-50 rounded-xl p-6 text-center border border-blue-100 hover:shadow-lg transition">
                        <div class="inline-flex items-center justify-center w-12 h-12 bg-blue-100 text-blue-600 rounded-full mb-4">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <h3 class="text-3xl font-bold text-blue-800">{data['duration']}</h3>
                        <p class="text-gray-600">ระยะเวลาเรียน (ปี/Years)</p>
                    </div>
                     <div class="bg-purple-50 rounded-xl p-6 text-center border border-purple-100 hover:shadow-lg transition">
                        <div class="inline-flex items-center justify-center w-12 h-12 bg-purple-100 text-purple-600 rounded-full mb-4">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <h3 class="text-3xl font-bold text-purple-800">~{data['tuition']}</h3>
                        <p class="text-gray-600">ค่าเทอม (บาท/เทอม)</p>
                    </div>
                </div>

                <div class="grid md:grid-cols-2 gap-12">
                    <!-- Why Study -->
                    <div>
                        <h3 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-600 to-blue-600 mb-6">ทำไมต้องเรียนที่นี่? (Insights)</h3>
                        <div class="space-y-4">
                             <div class="flex items-start">
                                <div class="w-10 h-10 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center mr-4 flex-shrink-0">1</div>
                                <div>
                                    <h4 class="font-bold text-gray-800">ความเชี่ยวชาญระดับสากล</h4>
                                    <p class="text-sm text-gray-500">คณาจารย์มีความเชี่ยวชาญและงานวิจัยที่เป็นที่ยอมรับในระดับนานาชาติ</p>
                                </div>
                             </div>
                             <div class="flex items-start">
                                <div class="w-10 h-10 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center mr-4 flex-shrink-0">2</div>
                                <div>
                                    <h4 class="font-bold text-gray-800">เครื่องมือและห้องปฏิบัติการทันสมัย</h4>
                                    <p class="text-sm text-gray-500">พร้อมด้วยเทคโนโลยี GIS, RS และห้องแล็บวิทยาศาสตร์สิ่งแวดล้อมที่ครบครัน</p>
                                </div>
                             </div>
                             <div class="flex items-start">
                                <div class="w-10 h-10 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center mr-4 flex-shrink-0">3</div>
                                <div>
                                    <h4 class="font-bold text-gray-800">เครือข่ายความร่วมมือ</h4>
                                    <p class="text-sm text-gray-500">มีเครือข่ายความร่วมมือกับภาครัฐและเอกชน ช่วยเพิ่มโอกาสในการฝึกงานและการทำงาน</p>
                                </div>
                             </div>
                        </div>
                    </div>

                    <!-- Careers -->
                    <div>
                        <h3 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-600 to-blue-600 mb-6">โอกาสทางอาชีพ (Careers)</h3>
                        <ul class="space-y-3 text-gray-700 bg-gray-50 p-6 rounded-xl border border-gray-100">
                             {career_html}
                        </ul>
                    </div>
                </div>

                <!-- Document Embed -->
                {bottom_content}

            </div>
        </div>
    </div>
    """
    return template

async def main():
    async with SessionLocal() as session:
        for slug, data in courses.items():
            print(f"Updating {slug}...")
            html_content = generate_html(data)
            
            # Check if page exists
            result = await session.execute(select(Page).where(Page.slug == slug))
            page = result.scalars().first()
            
            if page:
                page.content = html_content
                page.title = data['title'] # Ensure title is consistent
            else:
                 print(f"Page {slug} not found, skipping...")
                 
        await session.commit()
        print("All pages updated successfully.")

if __name__ == "__main__":
    asyncio.run(main())
