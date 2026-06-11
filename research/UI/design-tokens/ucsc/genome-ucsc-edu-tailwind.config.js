/** @type {import('tailwindcss').Config} */
export default {
  theme: {
    extend: {
    colors: {
        'neutral-50': '#000000',
        foreground: '#000000'
    },
    fontFamily: {
        sans: [
            'Helvetica',
            'sans-serif'
        ],
        body: [
            'Times',
            'sans-serif'
        ],
        font2: [
            'Arial',
            'sans-serif'
        ]
    },
    fontSize: {
        '16': [
            '16px',
            {
                lineHeight: 'normal'
            }
        ],
        '13.3333': [
            '13.3333px',
            {
                lineHeight: 'normal'
            }
        ]
    },
    spacing: {
        '0': '8px',
        '1': '21px'
    }
},
  },
};
