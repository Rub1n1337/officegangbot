// Palette remapped to the "Iris" design language (Claude Design redesign):
// near-black tinted dark surfaces, a lighter violet accent, and soft shadows.
// The whole app reskins from here because components read these scales through
// the semantic tokens (Brand, CardBackground, MainBackground, TextPrimary/…)
// and the light/dark objects below.
export const colors = {
  // Violet accent ramp. brand.400 = dark accent (#8B7CFF), brand.500 = light
  // accent (#6E56F5); the `action` button gradient blends 400↔500.
  brand: {
    100: '#EDE9FF',
    200: '#A99BFF', // accent-ink (lighter, for icons/links on dark)
    300: '#8B7CFF',
    400: '#8B7CFF', // dark Brand
    500: '#6E56F5', // light Brand / accent-2
    600: '#5B44E6',
    700: '#4A36C0',
    800: '#3A2A99',
    900: '#241A5E',
  },
  brandAlpha: {
    500: '#8b7cff99',
    100: '#8b7cff24',
  },
  // Light surfaces + gray text. 300 = light page bg, 900 = light primary text.
  secondaryGray: {
    100: '#EEEDF6', // inset
    200: '#F5F4FB', // surface-2
    300: '#F3F3F8', // page bg
    400: '#E9E7F2',
    500: '#9795A8', // text-3
    600: '#6B6980', // text-2
    700: '#56546B',
    800: '#3A3850',
    900: '#1A1830', // primary text
  },
  red: {
    400: '#F16A6A', // dark red
    500: '#E5484D',
    600: '#D33F44',
  },
  blue: {
    50: '#EFF4FB',
    500: '#3965FF',
  },
  orange: {
    100: '#FBEFD6',
    400: '#F5B14C', // amber (dark)
    500: '#D9880A',
  },
  green: {
    100: '#E7F8EF',
    400: '#3FD07E', // dark green
    500: '#12A150',
    600: '#0E8A44',
  },
  // Dark surfaces, darkest at 900. 900 = page bg, 800 = card, 700 = raised,
  // 600 = inset.
  navy: {
    50: '#9A9AB0', // text-2 on dark
    100: '#7E7E96', // text-3 on dark
    200: '#52526E',
    300: '#3A3A55',
    400: '#2C2C44',
    500: '#23233A',
    600: '#1B1B29', // inset
    700: '#181826', // raised surface
    800: '#14141F', // card
    900: '#0A0A14', // page bg
  },
  gray: {
    100: '#FAFCFE',
    500: '#6B6980',
  },
};

export const light = {
  globalBg: 'secondaryGray.300',
  brand: 'brand.500',
  textColorPrimary: 'secondaryGray.900',
  textColorSecondary: 'secondaryGray.600',
  cardBg: 'white',
  shadow: '0 16px 36px -20px rgba(80, 70, 150, 0.28)',
};

export const dark = {
  globalBg: 'navy.900',
  brand: 'brand.400',
  textColorPrimary: 'white',
  textColorSecondary: 'navy.50',
  cardBg: 'navy.800',
  shadow: '0 24px 50px -30px rgba(0, 0, 0, 0.7)',
};
