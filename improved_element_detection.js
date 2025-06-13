// Helper to get element name
const getName = (el) => {
    // Try aria-label (most descriptive and accessible)
    if (el.getAttribute('aria-label')) 
        return el.getAttribute('aria-label').trim();
    
    // Try associated label
    if (el.labels && el.labels.length) 
        return el.labels[0].textContent.trim();
    
    // Try placeholder
    if (el.getAttribute('placeholder')) 
        return el.getAttribute('placeholder').trim();
    
    // Try data attributes (commonly used for testing and identification)
    if (el.getAttribute('data-testid'))
        return el.getAttribute('data-testid').replace(/-/g, ' ').trim();
    
    if (el.getAttribute('data-id'))
        return el.getAttribute('data-id').replace(/-/g, ' ').trim();
        
    if (el.getAttribute('data-name'))
        return el.getAttribute('data-name').trim();
    
    // Try value for inputs
    if (el.value && typeof el.value === 'string' && el.value.trim()) 
        return el.value.trim();
    
    // Try inner text
    if (el.innerText && el.innerText.trim()) 
        return el.innerText.trim();
    
    // Try title attribute
    if (el.getAttribute('title'))
        return el.getAttribute('title').trim();
        
    // Try name or id but make them more readable
    if (el.getAttribute('name'))
        return el.getAttribute('name').replace(/[-_]/g, ' ').trim();
        
    if (el.id)
        return el.id.replace(/[-_]/g, ' ').trim();
    
    // If we have a button or link with no text, check for icon-only buttons
    const tagName = el.tagName.toLowerCase();
    if ((tagName === 'button' || tagName === 'a') && el.querySelector('i, svg, img')) {
        // Check for common icon classes
        const iconEl = el.querySelector('i, svg, img');
        const classList = Array.from(iconEl.classList || []);
        
        // Look for common icon patterns
        for (const cls of classList) {
            if (cls.includes('search')) return 'Search Button';
            if (cls.includes('delete') || cls.includes('trash')) return 'Delete Button';
            if (cls.includes('edit') || cls.includes('pencil')) return 'Edit Button';
            if (cls.includes('add') || cls.includes('plus')) return 'Add Button';
            if (cls.includes('save')) return 'Save Button';
            if (cls.includes('cancel') || cls.includes('close')) return 'Cancel Button';
            if (cls.includes('menu') || cls.includes('hamburger')) return 'Menu Button';
        }
        
        // If no specific icon found, use a generic but descriptive name
        return `${tagName === 'a' ? 'Icon Link' : 'Icon Button'}`;
    }
    
    // For select elements, try to be more descriptive
    if (tagName === 'select') {
        // Look at nearby labels or previous siblings for context
        let label = '';
        
        // Check for label with 'for' attribute
        if (el.id) {
            const labelEl = document.querySelector(`label[for="${el.id}"]`);
            if (labelEl) return labelEl.textContent.trim() + ' Dropdown';
        }
        
        // Check previous siblings for text
        let sibling = el.previousElementSibling;
        if (sibling && sibling.textContent.trim()) {
            return sibling.textContent.trim() + ' Dropdown';
        }
        
        return 'Dropdown Menu';
    }
    
    // Avoid returning just generic tag names
    if (tagName === 'a') return 'Link';
    if (tagName === 'button') return 'Button';
    if (tagName === 'input') return `${el.getAttribute('type') || 'Input'} Field`;
    
    // Last resort: element tag with position info
    const parent = el.parentElement;
    if (parent) {
        const children = Array.from(parent.children);
        const index = children.indexOf(el);
        if (index !== -1) {
            return `${tagName.charAt(0).toUpperCase() + tagName.slice(1)} ${index + 1}`;
        }
    }
    
    return tagName.charAt(0).toUpperCase() + tagName.slice(1);
}; 