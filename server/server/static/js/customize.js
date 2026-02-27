function openCustomize(){
  document.getElementById('customize-modal').classList.remove('hidden');
}
function closeCustomize(){
  document.getElementById('customize-modal').classList.add('hidden');
}

function applyCustomize(){
  const theme = document.getElementById('ui-theme').value;
  const accent = document.getElementById('ui-accent').value;
  const font = document.getElementById('ui-font').value;

  // Apply theme
  if(theme === 'dark') document.body.classList.add('theme-dark'); else document.body.classList.remove('theme-dark');

  // Apply accent
  document.documentElement.style.setProperty('--accent', accent);

  // Apply font (simple mapping for common fonts)
  let fontStack = 'Outfit, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial';
  if(font === 'Inter') fontStack = 'Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial';
  if(font === 'Poppins') fontStack = 'Poppins, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial';
  document.documentElement.style.setProperty('--ui-font', fontStack);

  // Persist
  localStorage.setItem('ui_settings', JSON.stringify({theme, accent, font}));
  closeCustomize();
}

function loadCustomize(){
  const raw = localStorage.getItem('ui_settings');
  if(!raw) return;
  try{
    const s = JSON.parse(raw);
    if(s.theme) document.getElementById('ui-theme').value = s.theme;
    if(s.accent) { document.getElementById('ui-accent').value = s.accent; document.documentElement.style.setProperty('--accent', s.accent); }
    if(s.font) document.getElementById('ui-font').value = s.font;
    if(s.theme === 'dark') document.body.classList.add('theme-dark'); else document.body.classList.remove('theme-dark');
    if(s.font) {
      let fontStack = 'Outfit, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial';
      if(s.font === 'Inter') fontStack = 'Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial';
      if(s.font === 'Poppins') fontStack = 'Poppins, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial';
      document.documentElement.style.setProperty('--ui-font', fontStack);
    }
  }catch(e){ console.warn('Failed to load UI settings', e); }
}

// Initialize on DOM ready
if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadCustomize); else loadCustomize();
