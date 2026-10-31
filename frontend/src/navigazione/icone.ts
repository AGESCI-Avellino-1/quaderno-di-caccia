/**
 * The icons of the menu and the pages (DEC-241): Bootstrap Icons (MIT), bundled as
 * inline SVG so they work offline and take the text colour. Only the ones listed here
 * end up in the app. Bootstrap Icons has no tent: `tenda` is drawn here, same grid.
 */
import arrowLeftRight from 'bootstrap-icons/icons/arrow-left-right.svg?raw'
import award from 'bootstrap-icons/icons/award.svg?raw'
import backpack from 'bootstrap-icons/icons/backpack.svg?raw'
import bank from 'bootstrap-icons/icons/bank.svg?raw'
import boxArrowRight from 'bootstrap-icons/icons/box-arrow-right.svg?raw'
import calendarEvent from 'bootstrap-icons/icons/calendar-event.svg?raw'
import calendar3 from 'bootstrap-icons/icons/calendar3.svg?raw'
import cashCoin from 'bootstrap-icons/icons/cash-coin.svg?raw'
import chevronDown from 'bootstrap-icons/icons/chevron-down.svg?raw'
import chevronUp from 'bootstrap-icons/icons/chevron-up.svg?raw'
import cloudUpload from 'bootstrap-icons/icons/cloud-upload.svg?raw'
import collection from 'bootstrap-icons/icons/collection.svg?raw'
import compass from 'bootstrap-icons/icons/compass.svg?raw'
import diagram3 from 'bootstrap-icons/icons/diagram-3.svg?raw'
import envelopeOpen from 'bootstrap-icons/icons/envelope-open.svg?raw'
import envelopePaper from 'bootstrap-icons/icons/envelope-paper.svg?raw'
import fileEarmarkText from 'bootstrap-icons/icons/file-earmark-text.svg?raw'
import flag from 'bootstrap-icons/icons/flag.svg?raw'
import gear from 'bootstrap-icons/icons/gear.svg?raw'
import incognito from 'bootstrap-icons/icons/incognito.svg?raw'
import journalText from 'bootstrap-icons/icons/journal-text.svg?raw'
import key from 'bootstrap-icons/icons/key.svg?raw'
import layoutSidebarInset from 'bootstrap-icons/icons/layout-sidebar-inset.svg?raw'
import link45deg from 'bootstrap-icons/icons/link-45deg.svg?raw'
import list from 'bootstrap-icons/icons/list.svg?raw'
import listOl from 'bootstrap-icons/icons/list-ol.svg?raw'
import listUl from 'bootstrap-icons/icons/list-ul.svg?raw'
import lock from 'bootstrap-icons/icons/lock.svg?raw'
import megaphone from 'bootstrap-icons/icons/megaphone.svg?raw'
import pencilSquare from 'bootstrap-icons/icons/pencil-square.svg?raw'
import people from 'bootstrap-icons/icons/people.svg?raw'
import personBadge from 'bootstrap-icons/icons/person-badge.svg?raw'
import personCircle from 'bootstrap-icons/icons/person-circle.svg?raw'
import personHeart from 'bootstrap-icons/icons/person-heart.svg?raw'
import personLinesFill from 'bootstrap-icons/icons/person-lines-fill.svg?raw'
import personPlus from 'bootstrap-icons/icons/person-plus.svg?raw'
import personVcard from 'bootstrap-icons/icons/person-vcard.svg?raw'
import receipt from 'bootstrap-icons/icons/receipt.svg?raw'
import receiptCutoff from 'bootstrap-icons/icons/receipt-cutoff.svg?raw'
import shieldCheck from 'bootstrap-icons/icons/shield-check.svg?raw'
import shieldLock from 'bootstrap-icons/icons/shield-lock.svg?raw'
import signpostSplit from 'bootstrap-icons/icons/signpost-split.svg?raw'
import sliders from 'bootstrap-icons/icons/sliders.svg?raw'
import tools from 'bootstrap-icons/icons/tools.svg?raw'
import typeBold from 'bootstrap-icons/icons/type-bold.svg?raw'
import typeItalic from 'bootstrap-icons/icons/type-italic.svg?raw'
import typeUnderline from 'bootstrap-icons/icons/type-underline.svg?raw'
import upload from 'bootstrap-icons/icons/upload.svg?raw'
import wallet2 from 'bootstrap-icons/icons/wallet2.svg?raw'
import xLg from 'bootstrap-icons/icons/x-lg.svg?raw'

const tenda = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-tenda" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 1.25 15.2 13.5H.8zm0 7.5-2.3 4.75h4.6zM0 13.5h16v1H0z"/></svg>`

export const ICONE = {
  'arrow-left-right': arrowLeftRight,
  award: award,
  backpack: backpack,
  bank: bank,
  'box-arrow-right': boxArrowRight,
  'calendar-event': calendarEvent,
  calendar3: calendar3,
  'cash-coin': cashCoin,
  'chevron-down': chevronDown,
  'chevron-up': chevronUp,
  'cloud-upload': cloudUpload,
  collection: collection,
  compass: compass,
  'diagram-3': diagram3,
  'envelope-open': envelopeOpen,
  'envelope-paper': envelopePaper,
  'file-earmark-text': fileEarmarkText,
  flag: flag,
  gear: gear,
  incognito: incognito,
  'journal-text': journalText,
  key: key,
  'layout-sidebar-inset': layoutSidebarInset,
  'link-45deg': link45deg,
  list: list,
  'list-ol': listOl,
  'list-ul': listUl,
  lock: lock,
  megaphone: megaphone,
  'pencil-square': pencilSquare,
  people: people,
  'person-badge': personBadge,
  'person-circle': personCircle,
  'person-heart': personHeart,
  'person-lines-fill': personLinesFill,
  'person-plus': personPlus,
  'person-vcard': personVcard,
  receipt: receipt,
  'receipt-cutoff': receiptCutoff,
  'shield-check': shieldCheck,
  'shield-lock': shieldLock,
  'signpost-split': signpostSplit,
  sliders: sliders,
  tools: tools,
  'type-bold': typeBold,
  'type-italic': typeItalic,
  'type-underline': typeUnderline,
  upload: upload,
  wallet2: wallet2,
  'x-lg': xLg,
  tenda,
} as const

export type NomeIcona = keyof typeof ICONE
