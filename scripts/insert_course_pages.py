import asyncio
from app.database import SessionLocal
from app.models import Page
from sqlalchemy import select
from datetime import datetime

PAGES_DATA = [
    # Bachelor's - Natural Resources & Environment
    {
        "slug": "bachelor-nre",
        "title": "หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม",
        "content": """
<div class="max-w-4xl mx-auto space-y-8">
    <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
        <h2 class="text-2xl font-bold text-gray-800 mb-4 border-l-4 border-green-500 pl-4">ข้อมูลทั่วไป (General Information)</h2>
        <p class="text-gray-600 mb-2">Bachelor of Science Program in Natural Resources and Environment</p>
        <a href="http://www.agi.nu.ac.th/wp-content/uploads/2021/10/NRED-general-information.pdf" target="_blank" class="inline-flex items-center px-4 py-2 bg-green-50 text-green-700 rounded-md hover:bg-green-100 transition-colors">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            Download PDF
        </a>
    </div>

    <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
        <h2 class="text-2xl font-bold text-gray-800 mb-4 border-l-4 border-blue-500 pl-4">แผนการศึกษา (Study Plan)</h2>
        <a href="http://www.agi.nu.ac.th/wp-content/uploads/2021/10/NRED-study-plan.pdf" target="_blank" class="inline-flex items-center px-4 py-2 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
            Download Study Plan
        </a>
    </div>

    <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
        <h2 class="text-2xl font-bold text-gray-800 mb-4 border-l-4 border-yellow-500 pl-4">คำอธิบายรายวิชา (Course Description)</h2>
        <a href="http://www.agi.nu.ac.th/wp-content/uploads/2021/10/NRED-course-description.pdf" target="_blank" class="inline-flex items-center px-4 py-2 bg-yellow-50 text-yellow-700 rounded-md hover:bg-yellow-100 transition-colors">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
            Download Description
        </a>
    </div>
    
    <div class="mt-8 text-center">
         <a href="https://www.admission.nu.ac.th/undergrad2.php" target="_blank" class="inline-block px-8 py-3 bg-gradient-to-r from-green-500 to-teal-500 text-white font-bold rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all">
            สมัครเรียน (Register Now)
         </a>
    </div>
</div>
"""
    },
    
    # Bachelor's - Geography
    {
        "slug": "bachelor-geo",
        "title": "หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาภูมิศาสตร์",
        "content": """
<div class="max-w-4xl mx-auto space-y-8">
    <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
        <h2 class="text-2xl font-bold text-gray-800 mb-4 border-l-4 border-indigo-500 pl-4">ข้อมูลทั่วไป (General Information)</h2>
        <p class="text-gray-600 mb-2">Bachelor of Science Program in Geography</p>
        <a href="http://www.agi.nu.ac.th/wp-content/uploads/2023/06/GIS-general-information-65.pdf" target="_blank" class="inline-flex items-center px-4 py-2 bg-indigo-50 text-indigo-700 rounded-md hover:bg-indigo-100 transition-colors">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            Download PDF
        </a>
    </div>

    <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
        <h2 class="text-2xl font-bold text-gray-800 mb-4 border-l-4 border-blue-500 pl-4">แผนการศึกษา (Study Plan)</h2>
        <a href="http://www.agi.nu.ac.th/wp-content/uploads/2023/06/GIS-study-plan-65.pdf" target="_blank" class="inline-flex items-center px-4 py-2 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
            Download Study Plan
        </a>
    </div>

    <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
        <h2 class="text-2xl font-bold text-gray-800 mb-4 border-l-4 border-purple-500 pl-4">คำอธิบายรายวิชา (Course Description)</h2>
        <a href="http://www.agi.nu.ac.th/wp-content/uploads/2023/06/GIS-course-description-65.pdf" target="_blank" class="inline-flex items-center px-4 py-2 bg-purple-50 text-purple-700 rounded-md hover:bg-purple-100 transition-colors">
             <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
            Download Description
        </a>
    </div>
    
    <div class="mt-8 text-center">
         <a href="https://www.admission.nu.ac.th/undergrad2.php" target="_blank" class="inline-block px-8 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-bold rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all">
            สมัครเรียน (Register Now)
         </a>
    </div>
</div>
"""
    },
    
    # Master's - NRE
    {
        "slug": "master-nre",
        "title": "หลักสูตรวิทยาศาสตรมหาบัณฑิต สาขาวิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม",
        "content": """
<div class="max-w-6xl mx-auto">
    <div class="mb-6 flex justify-between items-center bg-gray-50 p-4 rounded-lg">
        <div>
           <p class="text-gray-600">Master of Science Program in Natural Resources and Environment</p>
        </div>
        <a href="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%A7%E0%B8%97%E0%B8%A1_%E0%B8%97%E0%B8%A3%E0%B8%B1%E0%B8%9E%E0%B8%A2%E0%B8%B2%E0%B8%81%E0%B8%A3%E0%B8%98%E0%B8%A3%E0%B8%A3%E0%B8%A1%E0%B8%8A%E0%B8%B2%E0%B8%95%E0%B8%B4%E0%B9%81%E0%B8%A5%E0%B8%B0%E0%B8%AA%E0%B8%B4%E0%B9%88%E0%B8%87%E0%B9%81%E0%B8%A7%E0%B8%94%E0%B8%A5%E0%B9%89%E0%B8%AD%E0%B8%A1.pdf" target="_blank" class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition">
            Download PDF
        </a>
    </div>
    <div class="w-full h-[800px] border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <embed src="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%A7%E0%B8%97%E0%B8%A1_%E0%B8%97%E0%B8%A3%E0%B8%B1%E0%B8%9E%E0%B8%A2%E0%B8%B2%E0%B8%81%E0%B8%A3%E0%B8%98%E0%B8%A3%E0%B8%A3%E0%B8%A1%E0%B8%8A%E0%B8%B2%E0%B8%95%E0%B8%B4%E0%B9%81%E0%B8%A5%E0%B8%B0%E0%B8%AA%E0%B8%B4%E0%B9%88%E0%B8%87%E0%B9%81%E0%B8%A7%E0%B8%94%E0%B8%A5%E0%B9%89%E0%B8%AD%E0%B8%A1.pdf" type="application/pdf" width="100%" height="100%">
    </div>
</div>
"""
    },

    # Master's - Geography
    {
        "slug": "master-geo",
        "title": "หลักสูตรวิทยาศาสตรมหาบัณฑิต สาขาวิชาภูมิศาสตร์",
        "content": """
<div class="max-w-6xl mx-auto">
    <div class="mb-6 flex justify-between items-center bg-gray-50 p-4 rounded-lg">
        <div>
           <p class="text-gray-600">Master of Science Program in Geography</p>
        </div>
        <a href="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%A7%E0%B8%97%E0%B8%A1-%E0%B8%A0%E0%B8%B9%E0%B8%A1%E0%B8%B4%E0%B8%A8%E0%B8%B2%E0%B8%AA%E0%B8%95%E0%B8%A3%E0%B9%8C.pdf" target="_blank" class="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition">
            Download PDF
        </a>
    </div>
    <div class="w-full h-[800px] border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <embed src="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%A7%E0%B8%97%E0%B8%A1-%E0%B8%A0%E0%B8%B9%E0%B8%A1%E0%B8%B4%E0%B8%A8%E0%B8%B2%E0%B8%AA%E0%B8%95%E0%B8%A3%E0%B9%8C.pdf" type="application/pdf" width="100%" height="100%">
    </div>
</div>
"""
    },

    # Master's - Env Sci
    {
        "slug": "master-env-sci",
        "title": "หลักสูตรวิทยาศาสตรมหาบัณฑิต สาขาวิชาวิทยาศาสตร์สิ่งแวดล้อม",
        "content": """
<div class="max-w-6xl mx-auto">
    <div class="mb-6 flex justify-between items-center bg-gray-50 p-4 rounded-lg">
        <div>
           <p class="text-gray-600">Master of Science Program in Environmental Science</p>
        </div>
        <a href="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%A7%E0%B8%97%E0%B8%A1-%E0%B8%A7%E0%B8%B4%E0%B8%97%E0%B8%A2%E0%B8%B2%E0%B8%A8%E0%B8%B2%E0%B8%AA%E0%B8%95%E0%B8%A3%E0%B9%8C%E0%B8%AA%E0%B8%B4%E0%B9%88%E0%B8%87%E0%B9%81%E0%B8%A7%E0%B8%94%E0%B8%A5%E0%B9%89%E0%B8%AD%E0%B8%A1.pdf" target="_blank" class="px-4 py-2 bg-teal-600 text-white rounded hover:bg-teal-700 transition">
            Download PDF
        </a>
    </div>
    <div class="w-full h-[800px] border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <embed src="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%A7%E0%B8%97%E0%B8%A1-%E0%B8%A7%E0%B8%B4%E0%B8%97%E0%B8%A2%E0%B8%B2%E0%B8%A8%E0%B8%B2%E0%B8%AA%E0%B8%95%E0%B8%A3%E0%B9%8C%E0%B8%AA%E0%B8%B4%E0%B9%88%E0%B8%87%E0%B9%81%E0%B8%A7%E0%B8%94%E0%B8%A5%E0%B9%89%E0%B8%AD%E0%B8%A1.pdf" type="application/pdf" width="100%" height="100%">
    </div>
</div>
"""
    },

    # PhD - NRE
    {
        "slug": "phd-nre",
        "title": "หลักสูตรปรัชญาดุษฎีบัณฑิต สาขาวิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม",
        "content": """
<div class="max-w-6xl mx-auto">
    <div class="mb-6 flex justify-between items-center bg-gray-50 p-4 rounded-lg">
        <div>
           <p class="text-gray-600">Doctor of Philosophy Program in Natural Resources and Environment</p>
        </div>
        <a href="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%9B%E0%B8%A3%E0%B8%94-%E0%B8%97%E0%B8%A3%E0%B8%B1%E0%B8%9E%E0%B8%A2%E0%B8%B2%E0%B8%81%E0%B8%A3%E0%B8%98%E0%B8%A3%E0%B8%A3%E0%B8%A1%E0%B8%8A%E0%B8%B2%E0%B8%95%E0%B8%B4%E0%B9%81%E0%B8%A5%E0%B8%B0%E0%B8%AA%E0%B8%B4%E0%B9%88%E0%B8%87%E0%B9%81%E0%B8%A7%E0%B8%94%E0%B8%A5%E0%B9%89%E0%B8%AD%E0%B8%A1.pdf" target="_blank" class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition">
            Download PDF
        </a>
    </div>
    <div class="w-full h-[800px] border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <embed src="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%9B%E0%B8%A3%E0%B8%94-%E0%B8%97%E0%B8%A3%E0%B8%B1%E0%B8%9E%E0%B8%A2%E0%B8%B2%E0%B8%81%E0%B8%A3%E0%B8%98%E0%B8%A3%E0%B8%A3%E0%B8%A1%E0%B8%8A%E0%B8%B2%E0%B8%95%E0%B8%B4%E0%B9%81%E0%B8%A5%E0%B8%B0%E0%B8%AA%E0%B8%B4%E0%B9%88%E0%B8%87%E0%B9%81%E0%B8%A7%E0%B8%94%E0%B8%A5%E0%B9%89%E0%B8%AD%E0%B8%A1.pdf" type="application/pdf" width="100%" height="100%">
    </div>
</div>
"""
    },

    # PhD - Env Sci
    {
        "slug": "phd-env-sci",
        "title": "หลักสูตรปรัชญาดุษฎีบัณฑิต สาขาวิชาวิทยาศาสตร์สิ่งแวดล้อม",
        "content": """
<div class="max-w-6xl mx-auto">
    <div class="mb-6 flex justify-between items-center bg-gray-50 p-4 rounded-lg">
        <div>
           <p class="text-gray-600">Doctor of Philosophy Program in Environmental Science</p>
        </div>
        <a href="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%9B%E0%B8%A3%E0%B8%94-%E0%B8%A7%E0%B8%B4%E0%B8%97%E0%B8%A2%E0%B8%B2%E0%B8%A8%E0%B8%B2%E0%B8%AA%E0%B8%95%E0%B8%A3%E0%B9%8C%E0%B8%AA%E0%B8%B4%E0%B9%88%E0%B8%87%E0%B9%81%E0%B8%A7%E0%B8%94%E0%B8%A5%E0%B9%89%E0%B8%AD%E0%B8%A1.pdf" target="_blank" class="px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700 transition">
            Download PDF
        </a>
    </div>
    <div class="w-full h-[800px] border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <embed src="https://www.agi.nu.ac.th/wp-content/uploads/2023/course/%E0%B8%9B%E0%B8%A3%E0%B8%94-%E0%B8%A7%E0%B8%B4%E0%B8%97%E0%B8%A2%E0%B8%B2%E0%B8%A8%E0%B8%B2%E0%B8%AA%E0%B8%95%E0%B8%A3%E0%B9%8C%E0%B8%AA%E0%B8%B4%E0%B9%88%E0%B8%87%E0%B9%81%E0%B8%A7%E0%B8%94%E0%B8%A5%E0%B9%89%E0%B8%AD%E0%B8%A1.pdf" type="application/pdf" width="100%" height="100%">
    </div>
</div>
"""
    }
]

async def main():
    print(f"Starting import for {len(PAGES_DATA)} pages...")
    async with SessionLocal() as session:
        for page_data in PAGES_DATA:
            slug = page_data['slug']
            print(f"Processing: {slug}")
            
            # Check existing
            result = await session.execute(select(Page).where(Page.slug == slug))
            existing_page = result.scalars().first()
            
            if existing_page:
                print(f"  - Update existing page: {slug}")
                existing_page.title = page_data['title']
                existing_page.content = page_data['content']
                existing_page.is_published = 1
                existing_page.updated_at = datetime.now()
            else:
                print(f"  - Create new page: {slug}")
                new_page = Page(
                    slug=slug,
                    title=page_data['title'],
                    content=page_data['content'],
                    template='page',
                    is_published=1
                )
                session.add(new_page)
        
        await session.commit()
    print("Import completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
