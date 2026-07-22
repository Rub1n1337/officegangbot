import { inputAnatomy } from '@chakra-ui/anatomy';
import { createMultiStyleConfigHelpers } from '@chakra-ui/react';
import { dark, light } from '../colors';

const { definePartsStyle, defineMultiStyleConfig } = createMultiStyleConfigHelpers(
  inputAnatomy.keys
);

const main = definePartsStyle({
  field: {
    border: '1px solid',
    borderRadius: '12px',
    fontSize: 'sm',
    h: '44px',
    px: '14px',
    _light: {
      color: 'secondaryGray.900',
      bg: 'secondaryGray.100',
      _placeholder: {
        color: 'secondaryGray.500',
      },
      _invalid: {
        borderColor: 'red.400',
      },
      borderColor: 'blackAlpha.200',
      _hover: { borderColor: 'brand.400' },
      _focus: { borderColor: 'brand.400', boxShadow: 'none' },
    },

    _dark: {
      color: 'white',
      bg: 'navy.600',
      _placeholder: {
        color: 'navy.100',
      },
      _invalid: {
        borderColor: 'red.400',
      },
      // whiteAlpha.200 on the dark inset was ~1.4:1 — below the WCAG 3:1
      // minimum for UI component boundaries.
      borderColor: 'whiteAlpha.300',
      _hover: { borderColor: 'brand.400' },
      _focus: { borderColor: 'brand.400', boxShadow: 'none' },
    },
  },
});

export const inputStyles = defineMultiStyleConfig({
  baseStyle: definePartsStyle({
    field: {
      fontWeight: 400,
      // Theme-aware text colour on the base style so EVERY input is legible in
      // both modes — inputs that don't pick the `main` variant (the members
      // search, the ⌘K palette, colour/emoji pickers) otherwise inherited the
      // light-mode body colour (a dark slate) and the typed text was nearly
      // invisible on the dark theme.
      _light: {
        color: 'secondaryGray.900',
        borderColor: 'secondaryGray.400',
      },
      _dark: {
        color: 'white',
        borderColor: 'navy.600',
      },
      borderRadius: '8px',
    },
  }),

  variants: {
    flushed: definePartsStyle({
      field: {
        _focus: {
          _dark: {
            borderColor: dark.brand,
          },
          _light: {
            borderColor: light.brand,
          },
          boxShadow: 'none',
        },

        fontSize: '2xl',
        fontWeight: '600',
        _light: {
          color: light.textColorPrimary,
          borderBottomColor: 'secondaryGray.400',
        },
        _dark: {
          color: dark.textColorPrimary,
          borderBottomColor: 'navy.600',
        },
      },
    }),
    main,
    focus: definePartsStyle({
      field: {
        ...main.field,
        _focus: {
          _light: {
            borderColor: 'brand.300',
          },
          _dark: {
            borderColor: 'brand.400',
          },
        },
      },
    }),
    auth: definePartsStyle({
      field: {
        bg: 'transparent',
        fontWeight: '500',
        _light: {
          color: 'navy.700',
          borderColor: 'secondaryGray.100',
        },
        _dark: {
          color: 'white',
          borderColor: 'rgba(135, 140, 189, 0.3)',
        },
        border: '1px solid',
        borderRadius: '16px',
        _placeholder: { color: 'secondaryGray.600', fontWeight: '400' },
      },
    }),
    authSecondary: definePartsStyle({
      field: {
        bg: 'transparent',
        border: '1px solid',
        borderColor: 'secondaryGray.100',
        borderRadius: '16px',
        _placeholder: { color: 'secondaryGray.600' },
      },
    }),
    search: definePartsStyle({
      field: {
        border: 'none',
        py: '11px',
        borderRadius: 'inherit',
        _placeholder: { color: 'secondaryGray.600' },
      },
    }),
  },
});
