/**
 * Editor runtime injected INTO the site iframe.
 * Exported as a string so it can be appended to the site's HTML before rendering in the editor.
 * It makes text editable, adds section hover toolbars, an "+ Add block" flow, and talks to the
 * parent React app via postMessage. On save, the parent asks for the cleaned HTML.
 */
export const EDITOR_RUNTIME = `
<style id="sg-editor-style">
  [data-sg-editable]{outline:1px dashed transparent;transition:outline-color .15s;cursor:text;border-radius:3px}
  [data-sg-editable]:hover{outline-color:rgba(0,85,255,.5)}
  [data-sg-editable]:focus{outline:2px solid #0055FF;background:rgba(0,85,255,.05)}
  section[data-sg-section]{position:relative}
  section[data-sg-section].sg-hover{outline:2px solid rgba(0,85,255,.6);outline-offset:-2px}
  .sg-sec-toolbar{position:absolute;top:8px;right:8px;z-index:99998;display:none;gap:4px;
    background:#111318;border:1px solid rgba(255,255,255,.15);border-radius:8px;padding:4px;
    box-shadow:0 8px 24px rgba(0,0,0,.4);font-family:system-ui,-apple-system,sans-serif}
  section[data-sg-section].sg-hover>.sg-sec-toolbar{display:flex}
  .sg-sec-toolbar button{background:transparent;border:0;color:#fff;width:28px;height:28px;cursor:pointer;
    border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:14px;line-height:1}
  .sg-sec-toolbar button:hover{background:rgba(255,255,255,.12)}
  .sg-sec-toolbar input[type=color]{width:28px;height:28px;border:0;background:transparent;cursor:pointer;padding:0}
  .sg-add-row{position:absolute;left:0;right:0;bottom:0;height:0;display:flex;justify-content:center;z-index:99997}
  section[data-sg-section].sg-hover>.sg-add-row{height:auto}
  .sg-add-btn{transform:translateY(50%);background:#0055FF;color:#fff;border:0;border-radius:20px;
    padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 14px rgba(0,85,255,.5);
    font-family:system-ui,sans-serif;display:none}
  section[data-sg-section].sg-hover>.sg-add-row .sg-add-btn{display:block}
  .sg-selected{outline:2px solid #0055FF !important;outline-offset:2px}
</style>
<script id="sg-editor-script">
(function(){
  var sections=[];
  function post(type,payload){parent.postMessage(Object.assign({sg:true,type:type},payload||{}),'*');}

  function makeEditable(root){
    var sel='h1,h2,h3,h4,h5,h6,p,span,a,button,li,figcaption,blockquote,label';
    root.querySelectorAll(sel).forEach(function(el){
      if(el.closest('.sg-sec-toolbar')||el.querySelector(sel))return; // leaf text nodes only
      if(!el.textContent.trim())return;
      el.setAttribute('data-sg-editable','1');
      el.setAttribute('contenteditable','true');
      el.addEventListener('click',function(e){
        if(el.tagName==='A'||el.tagName==='BUTTON'){e.preventDefault();}
      });
      el.addEventListener('input',function(){post('dirty');});
    });
  }

  var ICONS={up:'↑',down:'↓',dup:'⧉',del:'🗑',add:'+ Add'};
  function buildToolbar(sec){
    var tb=document.createElement('div');tb.className='sg-sec-toolbar';tb.setAttribute('contenteditable','false');
    function btn(t,title,fn){var b=document.createElement('button');b.textContent=t;b.title=title;b.setAttribute('contenteditable','false');
      b.addEventListener('click',function(e){e.stopPropagation();e.preventDefault();fn();post('dirty');});return b;}
    tb.appendChild(btn(ICONS.up,'Move up',function(){var p=sec.previousElementSibling;if(p&&p.hasAttribute('data-sg-section'))sec.parentNode.insertBefore(sec,p);}));
    tb.appendChild(btn(ICONS.down,'Move down',function(){var n=sec.nextElementSibling;if(n&&n.hasAttribute('data-sg-section'))sec.parentNode.insertBefore(n,sec);}));
    tb.appendChild(btn(ICONS.dup,'Duplicate',function(){var c=sec.cloneNode(true);sec.parentNode.insertBefore(c,sec.nextSibling);enhance(c);}));
    var color=document.createElement('input');color.type='color';color.title='Background color';color.setAttribute('contenteditable','false');
    color.addEventListener('input',function(e){sec.style.background=e.target.value;post('dirty');});
    color.addEventListener('click',function(e){e.stopPropagation();});
    tb.appendChild(color);
    tb.appendChild(btn(ICONS.del,'Delete section',function(){if(sections.length>1){sec.remove();}}));
    return tb;
  }

  function buildAddRow(sec){
    var row=document.createElement('div');row.className='sg-add-row';row.setAttribute('contenteditable','false');
    var b=document.createElement('button');b.className='sg-add-btn';b.textContent=ICONS.add;b.setAttribute('contenteditable','false');
    b.addEventListener('click',function(e){e.stopPropagation();e.preventDefault();
      var r=sec.getBoundingClientRect();
      post('open-add',{sectionId:sec.getAttribute('data-sg-id')});
    });
    row.appendChild(b);return row;
  }

  function enhance(sec){
    if(!sec.hasAttribute('data-sg-id'))sec.setAttribute('data-sg-id','s'+Math.random().toString(36).slice(2,8));
    sec.setAttribute('data-sg-section','1');
    if(!sec.querySelector(':scope>.sg-sec-toolbar'))sec.appendChild(buildToolbar(sec));
    if(!sec.querySelector(':scope>.sg-add-row'))sec.appendChild(buildAddRow(sec));
    sec.addEventListener('mouseenter',function(){sec.classList.add('sg-hover');});
    sec.addEventListener('mouseleave',function(){sec.classList.remove('sg-hover');});
    makeEditable(sec);
  }

  function init(){
    var secs=document.querySelectorAll('body section');
    if(!secs.length){ // fallback: treat top-level divs/header/footer as sections
      secs=document.querySelectorAll('body>header,body>footer,body>main>*,body>div');
    }
    sections=Array.prototype.slice.call(secs);
    sections.forEach(enhance);
    // footer that isn't a section
    var f=document.querySelector('footer');if(f&&!f.hasAttribute('data-sg-section')){enhance(f);sections.push(f);}
    makeEditable(document.body);
    post('ready',{sections:sections.length});
  }

  // ---- add block ----
  var BLOCKS={
    subheadline:function(){var h=document.createElement('h3');h.textContent='New sub-headline';return h;},
    text:function(){var p=document.createElement('p');p.textContent='New paragraph. Click to edit this text.';return p;},
    button:function(){var a=document.createElement('a');a.href='#contact';a.textContent='New Button';
      a.style.cssText='display:inline-block;padding:12px 24px;background:#0055FF;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;margin:8px 0';return a;},
    image:function(){var img=document.createElement('img');img.src='https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1200&q=70';img.alt='New image';img.style.cssText='max-width:100%;border-radius:12px;margin:12px 0';return img;},
    list:function(){var ul=document.createElement('ul');ul.style.cssText='margin:12px 0;padding-left:20px';['First item','Second item','Third item'].forEach(function(t){var li=document.createElement('li');li.textContent=t;ul.appendChild(li);});return ul;},
    quicklinks:function(){var nav=document.createElement('div');nav.style.cssText='display:flex;gap:20px;flex-wrap:wrap;margin:16px 0';
      ['Home','About','Services','Contact'].forEach(function(t){var a=document.createElement('a');a.href='#';a.textContent=t;a.style.cssText='color:inherit;text-decoration:none;opacity:.8';nav.appendChild(a);});return nav;},
    divider:function(){var hr=document.createElement('hr');hr.style.cssText='border:0;border-top:1px solid rgba(0,0,0,.12);margin:24px 0';return hr;},
    spacer:function(){var d=document.createElement('div');d.style.height='48px';d.setAttribute('data-sg-spacer','1');return d;}
  };
  function addBlock(sectionId,kind){
    var sec=document.querySelector('[data-sg-id="'+sectionId+'"]');if(!sec||!BLOCKS[kind])return;
    var el=BLOCKS[kind]();
    var toolbar=sec.querySelector(':scope>.sg-sec-toolbar');
    var addrow=sec.querySelector(':scope>.sg-add-row');
    // insert before the add row / toolbar so it lands inside the visible content
    sec.insertBefore(el,addrow||null);
    if(el.querySelectorAll)makeEditable(sec);
    else if(el.setAttribute){el.setAttribute('data-sg-editable','1');el.setAttribute('contenteditable','true');}
    // make the new element itself editable if it's a leaf
    ['H3','P','A','LI'].indexOf(el.tagName)>-1 && (el.setAttribute('data-sg-editable','1'),el.setAttribute('contenteditable','true'));
    post('dirty');
  }

  // ---- serialize (clean) ----
  function cleanHtml(){
    var clone=document.documentElement.cloneNode(true);
    // strip editor chrome
    clone.querySelectorAll('.sg-sec-toolbar,.sg-add-row,#sg-editor-style,#sg-editor-script').forEach(function(n){n.remove();});
    clone.querySelectorAll('[contenteditable]').forEach(function(n){n.removeAttribute('contenteditable');});
    clone.querySelectorAll('[data-sg-editable],[data-sg-section],[data-sg-id],[data-sg-spacer]').forEach(function(n){
      n.removeAttribute('data-sg-editable');n.removeAttribute('data-sg-section');n.removeAttribute('data-sg-id');n.removeAttribute('data-sg-spacer');
    });
    clone.querySelectorAll('.sg-hover,.sg-selected').forEach(function(n){n.classList.remove('sg-hover');n.classList.remove('sg-selected');});
    return '<!DOCTYPE html>\\n'+clone.outerHTML;
  }

  window.addEventListener('message',function(e){
    var d=e.data||{};if(!d.sg)return;
    if(d.type==='add-block')addBlock(d.sectionId,d.kind);
    if(d.type==='request-html')post('html',{html:cleanHtml()});
  });

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
</script>
`;
