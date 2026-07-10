import { mode } from '@chakra-ui/theme-tools';
import { defineStyle, defineStyleConfig } from '@chakra-ui/react';
import { light, dark } from '../colors';

export const textareaStyles = defineStyleConfig({
  baseStyle: defineStyle((props) => ({
    fontWeight: 400,
    borderRadius: '8px',
    fontSize: 'md',
    bg: mode(light.globalBg, dark.globalBg)(props),
    rounded: 'lg',
    border: 0,
    _focus: { boxShadow: 'none' },
  })),
  variants: {
    main: defineStyle((props: any) => ({
      bg: mode('secondaryGray.100', 'navy.600')(props),
      border: '1px solid',
      color: mode('secondaryGray.900', 'white')(props),
      borderColor: mode('blackAlpha.200', 'whiteAlpha.200')(props),
      borderRadius: '12px',
      fontSize: 'sm',
      p: '13px 14px',
      _hover: { borderColor: 'brand.400' },
      _focus: { borderColor: 'brand.400', boxShadow: 'none' },
      _placeholder: {
        color: mode('secondaryGray.500', 'navy.100')(props),
      },
    })),
    glass: {
      borderColor: 'var(--border-color)',
      border: '1px solid',
      _light: {
        bg: 'secondaryGray.300',
        borderColor: 'blackAlpha.200',
        _invalid: {
          borderColor: 'red.300',
        },
        _placeholder: {
          color: 'secondaryGray.700',
        },
      },
      _dark: {
        bg: 'blackAlpha.300',
        borderColor: 'whiteAlpha.200',
        _invalid: {
          borderColor: 'red.400',
        },
        _placeholder: {
          color: 'secondaryGray.600',
        },
      },
    },
  },
});
