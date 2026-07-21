import { extendTheme } from '@chakra-ui/react';
import { buttonStyles } from './components/button';
import { inputStyles } from './components/input';
import { sliderStyles } from './components/slider';
import { textareaStyles } from './components/textarea';
import { switchStyles } from './components/switch';
import { breakpoints } from './breakpoints';
import { modalStyles } from './components/modal';
import { avatarStyles } from './components/avatar';
import { menuTheme } from './components/menu';
import { skeletonStyles } from './components/skeleton';
import { tabsStyles } from './components/tabs';
import { cardStyles } from './components/card';
import { globalStyles } from '../styles/global';
import { colors, dark, light } from './colors';
import { selectStyles } from './components/select';
import { popoverStyles } from './components/popover';

export const theme = extendTheme({
  breakpoints,
  colors,
  styles: {
    global: globalStyles,
  },
  fonts: {
    heading: `'Onest',ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,Noto Sans,sans-serif`,
    body: `'Onest',ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica Neue,Arial,Noto Sans,sans-serif`,
  },
  // The single type scale. Every size + line-height is a multiple of the 4px
  // baseline grid, so text in adjacent cards/columns lands on one rhythm. Used
  // via `textStyle="body"` etc., replacing the ~20 raw px font sizes (13.5,
  // 11.5, 10.5 …) that had accumulated. Weightless styles (body/caption/micro)
  // leave fontWeight to the component; the heading styles own their weight.
  textStyles: {
    overline: { fontSize: '11px', lineHeight: '16px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' },
    micro: { fontSize: '11px', lineHeight: '16px' },
    caption: { fontSize: '12px', lineHeight: '16px' },
    body: { fontSize: '14px', lineHeight: '20px' },
    h3: { fontSize: '15px', lineHeight: '20px', fontWeight: 700 },
    h2: { fontSize: '20px', lineHeight: '28px', fontWeight: 800, letterSpacing: '-0.01em' },
    h1: { fontSize: '26px', lineHeight: '32px', fontWeight: 800, letterSpacing: '-0.02em' },
    stat: { fontSize: '28px', lineHeight: '32px', fontWeight: 800, letterSpacing: '-0.02em' },
  },
  components: {
    Button: buttonStyles,
    Switch: switchStyles,
    Modal: modalStyles,
    Avatar: avatarStyles,
    Menu: menuTheme,
    RangeSlider: sliderStyles,
    Input: inputStyles,
    Textarea: textareaStyles,
    Skeleton: skeletonStyles,
    Tabs: tabsStyles,
    Card: cardStyles,
    Select: selectStyles,
    Popover: popoverStyles,
  },
  semanticTokens: {
    shadows: {
      normal: {
        default: light.shadow,
        _dark: dark.shadow,
      },
    },
    colors: {
      TextPrimary: {
        default: light.textColorPrimary,
        _dark: dark.textColorPrimary,
      },
      TextSecondary: {
        default: light.textColorSecondary,
        _dark: dark.textColorSecondary,
      },
      MainBackground: {
        default: light.globalBg,
        _dark: dark.globalBg,
      },
      InputBackground: {
        default: 'secondaryGray.300',
        _dark: 'blackAlpha.300',
      },
      InputBorder: {
        default: 'blackAlpha.200',
        _dark: 'whiteAlpha.200',
      },
      Brand: {
        default: light.brand,
        _dark: dark.brand,
      },
      CardBackground: {
        default: light.cardBg,
        _dark: dark.cardBg,
      },
      // Subtle card outline so nested cards are visibly separated on both
      // themes (a shadow alone disappears on the dark background).
      CardBorder: {
        default: 'blackAlpha.200',
        _dark: 'whiteAlpha.200',
      },
    },
  },
});
