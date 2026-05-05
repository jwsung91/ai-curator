/**
 * TOC active highlight logic
 */
export function initTOC() {
  const tocLinks = document.querySelectorAll<HTMLAnchorElement>('a[data-toc-slug]');
  if (tocLinks.length === 0) return;

  const headingEls = Array.from(tocLinks).map(a => {
    return document.getElementById(a.dataset.tocSlug!);
  }).filter(Boolean) as HTMLElement[];

  let activeSlug = '';
  const setActive = (slug: string) => {
    if (slug === activeSlug) return;
    activeSlug = slug;
    tocLinks.forEach(a => {
      const isActive = a.dataset.tocSlug === slug;
      a.classList.toggle('text-blue-600', isActive);
      a.classList.toggle('dark:text-blue-400', isActive);
      a.classList.toggle('font-medium', isActive);
      a.classList.toggle('text-zinc-600', !isActive);
      a.classList.toggle('dark:text-zinc-400', !isActive);
    });
  };

  const observer = new IntersectionObserver(
    entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          setActive(entry.target.id);
          break;
        }
      }
    },
    { rootMargin: '-10% 0px -80% 0px', threshold: 0 }
  );

  headingEls.forEach(el => observer.observe(el));
  if (headingEls[0]) setActive(headingEls[0].id);
}

/**
 * Citation tooltip logic
 */
export function initCitationTooltips() {
  const refMap: Record<string, { title: string; url: string; source: string }> = {};

  // Build the reference map from the citation source list
  document.querySelectorAll<HTMLElement>('span[id^="ref-"]').forEach(span => {
    const id = span.id;
    
    // 1. Try to get data from attributes first (Robust)
    const dTitle = span.dataset.title;
    const dUrl = span.dataset.url;
    const dSource = span.dataset.source;

    if (dTitle && dUrl) {
      refMap[id] = { title: dTitle, url: dUrl, source: dSource ?? '' };
      return;
    }

    // 2. Fallback: Search siblings (Legacy)
    const block = span.closest('p, div, li') ?? span;
    let el: Element | null = block;
    let foundLink: HTMLAnchorElement | null = null;
    let limit = 5;

    while (el && limit > 0) {
      foundLink = el.querySelector<HTMLAnchorElement>('a[href^="http"]');
      if (foundLink) break;
      if (el !== block && el.querySelector('span[id^="ref-"]')) break;
      el = el.nextElementSibling;
      limit--;
    }

    if (foundLink) {
      const text = el?.textContent ?? '';
      const dashIdx = text.indexOf('—');
      const source = dashIdx >= 0 ? text.slice(dashIdx + 1).trim().replace(/^\*|\*$/g, '') : '';
      refMap[id] = {
        title: foundLink.textContent?.trim() ?? '',
        url: foundLink.href,
        source
      };
    }
  });

  const tip = document.createElement('div');
  Object.assign(tip.style, {
    position: 'fixed', zIndex: '9999', maxWidth: '380px', minWidth: '200px',
    padding: '10px 14px', borderRadius: '10px', fontSize: '13px', lineHeight: '1.55',
    opacity: '0', transition: 'opacity 0.12s ease', display: 'none',
    boxShadow: '0 6px 24px rgba(0,0,0,0.13)'
  });
  document.body.appendChild(tip);

  function syncTheme() {
    const dark = document.documentElement.classList.contains('dark');
    tip.style.background = dark ? '#27272a' : '#ffffff';
    tip.style.border = dark ? '1px solid #3f3f46' : '1px solid #e4e4e7';
    tip.style.color = dark ? '#d4d4d8' : '#27272a';
  }
  syncTheme();
  
  const themeObserver = new MutationObserver(syncTheme);
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

  let hideTimer: ReturnType<typeof setTimeout>;

  function buildTipContent(ref: { title: string; url: string; source: string }) {
    tip.textContent = '';
    const dark = document.documentElement.classList.contains('dark');
    
    const titleEl = document.createElement('div');
    titleEl.style.cssText = 'font-weight:600;margin-bottom:3px;word-break:break-word;';
    titleEl.textContent = ref.title;
    tip.appendChild(titleEl);

    if (ref.source) {
      const sourceEl = document.createElement('div');
      sourceEl.style.cssText = 'font-size:11px;opacity:0.55;margin-bottom:7px;';
      sourceEl.textContent = ref.source;
      tip.appendChild(sourceEl);
    }

    const linkEl = document.createElement('a');
    linkEl.href = ref.url;
    linkEl.target = '_blank';
    linkEl.rel = 'noopener noreferrer';
    linkEl.style.cssText = `font-size:11px;color:${dark ? '#93c5fd' : '#2563eb'};word-break:break-all;text-decoration:none;`;
    linkEl.textContent = ref.url;
    tip.appendChild(linkEl);
  }

  function showTip(anchor: HTMLAnchorElement, id: string) {
    clearTimeout(hideTimer);
    const ref = refMap[id];
    if (!ref) return;

    buildTipContent(ref);
    syncTheme();
    tip.style.display = 'block';
    
    const rect = anchor.getBoundingClientRect();
    const pad = 12;

    requestAnimationFrame(() => {
      const tipW = Math.min(380, window.innerWidth - pad * 2);
      tip.style.maxWidth = `${tipW}px`;
      const left = Math.max(pad, Math.min(rect.left, window.innerWidth - tipW - pad));
      tip.style.left = `${left}px`;
      tip.style.top = `${rect.top - 8}px`;
      tip.style.transform = 'translateY(-100%)';
      
      const tipRect = tip.getBoundingClientRect();
      if (tipRect.top < pad) {
        tip.style.top = `${rect.bottom + 8}px`;
        tip.style.transform = 'none';
      }
      tip.style.opacity = '1';
    });
  }

  function hideTip() {
    hideTimer = setTimeout(() => {
      tip.style.opacity = '0';
      setTimeout(() => { tip.style.display = 'none'; }, 120);
    }, 80);
  }

  tip.addEventListener('mouseenter', () => clearTimeout(hideTimer));
  tip.addEventListener('mouseleave', hideTip);

  document.querySelectorAll<HTMLAnchorElement>('a[href^="#ref-"]').forEach(anchor => {
    const id = anchor.getAttribute('href')!.slice(1);
    anchor.addEventListener('mouseenter', () => showTip(anchor, id));
    anchor.addEventListener('mouseleave', hideTip);
  });
}
