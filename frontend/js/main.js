const BACKEND_URL = "http://localhost:8000"; // Ganti jika port backend berbeda

const videoUrlInput = document.getElementById('videoUrl');
const btnFetch = document.getElementById('btnFetch');
const loadingIndicator = document.getElementById('loading');
const resultCard = document.getElementById('resultCard');
const videoThumbnail = document.getElementById('videoThumbnail');
const videoDuration = document.getElementById('videoDuration');
const videoTitle = document.getElementById('videoTitle');
const videoSource = document.getElementById('videoSource');
const formatSelect = document.getElementById('formatSelect');
const btnDownload = document.getElementById('btnDownload');
const tabBtns = document.querySelectorAll('.tab-btn');
const audioWarning = document.getElementById('audioWarning');
const inputIcon = document.getElementById('input-icon');
const clearBtn = document.getElementById('clearBtn');
const fetchForm = document.getElementById('fetchForm');

const PLATFORM_ICON = {
    youtube: 'fa-brands fa-youtube',
    tiktok: 'fa-brands fa-tiktok',
    instagram: 'fa-brands fa-instagram'
};

const PLACEHOLDER = {
    youtube: 'Tempel link video YouTube di sini...',
    tiktok: 'Tempel link video TikTok di sini...',
    instagram: 'Tempel link foto/video Instagram di sini...'
};

// Carousel Elements
const carouselResultCard = document.getElementById('carouselResultCard');
const carouselTitle = document.getElementById('carouselTitle');
const carouselImage = document.getElementById('carouselImage');
const carouselPrev = document.getElementById('carouselPrev');
const carouselNext = document.getElementById('carouselNext');
const carouselDots = document.getElementById('carouselDots');
const btnDownloadSlide = document.getElementById('btnDownloadSlide');
const btnDownloadCarouselVideo = document.getElementById('btnDownloadCarouselVideo');
const btnDownloadCarouselMp3 = document.getElementById('btnDownloadCarouselMp3');

let currentCarouselItems = [];
let currentCarouselIndex = 0;

let currentPlatform = 'youtube';
let currentVideoData = null;
let currentVideoUrl = null;

// Validasi URL per platform
const URL_PATTERNS = {
    youtube: /(?:youtu\.be\/|youtube\.com\/(?:watch|shorts|live|embed|playlist))/i,
    tiktok: /tiktok\.com\//i,
    instagram: /(?:instagram\.com|instagr\.am)\//i
};

function isValidUrl() {
    const pattern = URL_PATTERNS[currentPlatform];
    return pattern ? pattern.test(videoUrlInput.value.trim()) : false;
}

function toggleClearBtn() {
    clearBtn.classList.toggle('hidden', !isValidUrl());
}

// Clear button logic
if (videoUrlInput && clearBtn) {
    videoUrlInput.addEventListener('input', toggleClearBtn);

    clearBtn.addEventListener('click', () => {
        videoUrlInput.value = '';
        clearBtn.classList.add('hidden');
        videoUrlInput.focus();
    });
}

// Tab switching logic
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.setAttribute('aria-pressed', String(b === btn)));

        currentPlatform = btn.dataset.platform;
        document.body.dataset.platform = currentPlatform;
        inputIcon.innerHTML = `<i class="${PLATFORM_ICON[currentPlatform]}" aria-hidden="true"></i>`;
        videoUrlInput.placeholder = PLACEHOLDER[currentPlatform];

        // Reset UI when switching platform
        videoUrlInput.value = '';
        if (clearBtn) clearBtn.classList.add('hidden');
        resultCard.classList.add('hidden');
        if (carouselResultCard) carouselResultCard.classList.add('hidden');
        formatSelect.innerHTML = '';
        btnDownload.href = '#';
        audioWarning.classList.add('hidden');
        loadingIndicator.classList.add('hidden');

        // Show/hide method options: TikTok doesn't need processing methods
        const methodContainer = document.getElementById('methodContainer');
        if (methodContainer) {
            methodContainer.classList.toggle('hidden', currentPlatform === 'tiktok');
        }

        videoSource.innerText = `Platform: ${currentPlatform.charAt(0).toUpperCase() + currentPlatform.slice(1)}`;
    });
});

const methodRadios = document.querySelectorAll('input[name="processMethod"]');
methodRadios.forEach(radio => {
    radio.addEventListener('change', () => {
        // Jika hasil ekstraksi sedang ditampilkan, perbarui link download tanpa me-refresh/fetch ulang
        if (!resultCard.classList.contains('hidden') && currentVideoData && currentVideoUrl) {
            updateDownloadLink(currentVideoData, currentVideoUrl);
        }
        // Perbarui juga link download untuk tampilan carousel
        if (carouselResultCard && !carouselResultCard.classList.contains('hidden') && currentVideoData && currentVideoUrl) {
            updateCarouselUI();
            
            const methodElem = document.querySelector('input[name="processMethod"]:checked');
            const selectedMethod = methodElem ? methodElem.value : 'ffmpeg';
            const cleanTitle = (currentVideoData.title || 'carousel').replace(/[\\/*?:"<>|]/g, '');
            btnDownloadCarouselMp3.href = `${BACKEND_URL}/api/download?url=${encodeURIComponent(currentVideoUrl)}&format_id=bestaudio/best&title=${encodeURIComponent(cleanTitle)}&ext=mp3&method=${selectedMethod}`;
        }
    });
});

const updateDownloadLink = (data, videoUrl) => {
    const selectedOption = formatSelect.options[formatSelect.selectedIndex];
    const selectedFormat = data.formats[formatSelect.value];
    
    if (selectedOption.dataset.hasAudio === 'false' || selectedOption.dataset.hasAudio === false) {
        audioWarning.classList.remove('hidden');
    } else {
        audioWarning.classList.add('hidden');
    }

    // Mengupdate href tombol download sesuai endpoint backend
    // Menambahkan format_id, title, ext, dan method (jika ada)
    const methodElem = document.querySelector('input[name="processMethod"]:checked');
    const selectedMethod = methodElem ? methodElem.value : '';
    btnDownload.href = `${BACKEND_URL}/api/download?url=${encodeURIComponent(videoUrl)}&format_id=${encodeURIComponent(selectedFormat.format_id)}&title=${encodeURIComponent(data.title)}&ext=${encodeURIComponent(selectedFormat.ext)}&method=${selectedMethod}`;
};

const updateCarouselUI = () => {
    if (!currentCarouselItems || currentCarouselItems.length === 0) return;
    const item = currentCarouselItems[currentCarouselIndex];
    carouselImage.src = item.thumbnail || '';
    
    // Update dots
    carouselDots.innerHTML = '';
    currentCarouselItems.forEach((_, idx) => {
        const dot = document.createElement('button');
        dot.type = 'button';
        dot.className = 'dot' + (idx === currentCarouselIndex ? ' is-active' : '');
        dot.setAttribute('aria-label', `Slide ${idx + 1}`);
        dot.onclick = () => {
            currentCarouselIndex = idx;
            updateCarouselUI();
        };
        carouselDots.appendChild(dot);
    });

    const cleanTitle = (item.title || 'slide').replace(/[\\/*?:"<>|]/g, '');
    const slideUrl = item.url || item.thumbnail;
    const fromUrl = (slideUrl.match(/\.(jpe?g|png|webp|mp4)(?:[?#]|$)/i) || [null, null])[1];
    // ext berasal dari backend (IG bisa slide video), fallback dari URL
    const slideExt = (item.ext || fromUrl || 'jpg').toLowerCase();
    btnDownloadSlide.href = `${BACKEND_URL}/api/download?url=${encodeURIComponent(slideUrl)}&format_id=direct&title=${encodeURIComponent(cleanTitle)}&ext=${slideExt}&method=ffmpeg`;
};

if (carouselPrev && carouselNext) {
    carouselPrev.addEventListener('click', () => {
        if (currentCarouselIndex > 0) {
            currentCarouselIndex--;
        } else {
            currentCarouselIndex = currentCarouselItems.length - 1;
        }
        updateCarouselUI();
    });

    carouselNext.addEventListener('click', () => {
        if (currentCarouselIndex < currentCarouselItems.length - 1) {
            currentCarouselIndex++;
        } else {
            currentCarouselIndex = 0;
        }
        updateCarouselUI();
    });
}

const renderCarousel = (data, url) => {
    carouselTitle.innerText = data.title || 'Carousel Post';
    currentCarouselItems = data.items || data.images || [];
    currentCarouselIndex = 0;
    
    if (currentCarouselItems.length > 0) {
        updateCarouselUI();
        
        const methodElem = document.querySelector('input[name="processMethod"]:checked');
        const selectedMethod = methodElem ? methodElem.value : 'ffmpeg';
        const cleanTitle = (data.title || 'carousel').replace(/[\\/*?:"<>|]/g, '');
        
        btnDownloadCarouselMp3.href = `${BACKEND_URL}/api/download?url=${encodeURIComponent(url)}&format_id=bestaudio/best&title=${encodeURIComponent(cleanTitle)}&ext=mp3&method=${selectedMethod}`;
        
        carouselResultCard.classList.remove('hidden');
    }
};

fetchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = videoUrlInput.value.trim();
    if (!url) {
        alert('Silakan masukkan URL video!');
        return;
    }

    const methodElem = document.querySelector('input[name="processMethod"]:checked');
    const selectedMethod = methodElem ? methodElem.value : '';

    // Tampilkan loading, sembunyikan hasil sebelumnya
    loadingIndicator.classList.remove('hidden');
    resultCard.classList.add('hidden');
    if (carouselResultCard) carouselResultCard.classList.add('hidden');
    audioWarning.classList.add('hidden');

    try {
        const response = await fetch(`${BACKEND_URL}/api/extract?url=${encodeURIComponent(url)}&method=${selectedMethod}`);
        const data = await response.json();
        
        currentVideoData = data;
        currentVideoUrl = url;

        if (data.status === 'success') {
            if (data.type === 'carousel') {
                renderCarousel(data, url);
            } else {
                videoTitle.innerText = data.title || 'Video Tanpa Judul';
                videoThumbnail.src = data.thumbnail || '';
                videoDuration.innerText = data.duration || '00:00';
                videoSource.innerText = `Platform: ${currentPlatform.charAt(0).toUpperCase() + currentPlatform.slice(1)}`;

                formatSelect.innerHTML = '';
                
                if (data.formats && data.formats.length > 0) {
                    data.formats.forEach((fmt, index) => {
                        const option = document.createElement('option');
                        option.value = index;
                        option.innerText = fmt.label;
                        option.dataset.hasAudio = fmt.has_audio;
                        formatSelect.appendChild(option);
                    });

                    formatSelect.onchange = () => updateDownloadLink(data, url);
                    updateDownloadLink(data, url); // Initialize first link
                    
                    resultCard.classList.remove('hidden');
                } else {
                    alert('Tidak ada format yang tersedia untuk video ini.');
                }
            }
        } else {
            alert(`Gagal mengambil video: ${data.message || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error fetching video:', error);
        alert('Terjadi kesalahan saat menghubungi server. Pastikan backend server berjalan.');
    } finally {
        loadingIndicator.classList.add('hidden');
    }
});