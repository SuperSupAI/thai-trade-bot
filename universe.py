"""รายชื่อหุ้น SET100 แบ่งกลุ่มอุตสาหกรรม (curated · แก้ไขได้)
หมายเหตุ: SET100 เปลี่ยนได้เรื่อยๆ — ลิสต์นี้เป็นตัวยอดนิยม/สภาพคล่องสูง
"""
# รายชื่อหุ้น SET ทั้งหมด (ประมาณ 800+ หุ้น) สำหรับ fallback เมื่อ investpy ล้มเหลว
ALL_SET_STOCKS = [
    "2S", "7UP", "A", "A5", "AAV", "ABICO", "ABM", "ABPIF", "ACAP", "ACC", "ACE", "ACG",
    "ACT", "ADVANC", "AEC", "AEG", "AH", "AHUAY", "AI", "AJ", "AJC", "AKAPAP", "AKP",
    "AMARIN", "AMATA", "AMC", "AMIN", "AMP", "AMPG", "ANAN", "ANANDA", "ANAREIT", "AOT",
    "AP", "APCS", "APD", "APHA", "APURE", "AQ", "AQUA", "AR", "ARCHI", "ASAP", "ASK",
    "ASIMAR", "ASIA", "ASP", "ATA", "ATL", "ATOM", "AU", "AUC", "AUTO", "AUCT", "AWC",
    "AWN", "AYUD", "B", "BA", "BAFS", "BAH", "BAKER", "BALCO", "BAMART", "BANPU", "BAP",
    "BARLI", "BATA", "BAY", "BAYN", "BBL", "BBC", "BBCAP", "BBS", "BBUK", "BC", "BCA",
    "BEC", "BEAUTY", "BED", "BEL", "BEM", "BF", "BFIT", "BFRESH", "BFS", "BFSQ", "BH",
    "BIG", "BJC", "BK", "BKBN", "BKCP", "BKD", "BKDCP", "BKI", "BKKCP", "BKME", "BKN",
    "BKPC", "BLA", "BLAND", "BLC", "BLT", "BLUW", "BMB", "BMCAP", "BMC", "BMOIL", "BMPT",
    "BMRI", "BMS", "BMT", "BNH", "BOL", "BOND", "BOSSQ", "BP", "BPCAP", "BPC", "BPHC",
    "BPI", "BPP", "BPSQ", "BR", "BRCP", "BRR", "BRS", "BSCO", "BSCP", "BSBM", "BSM",
    "BTS", "BTW", "BUA", "BUCK", "BUCO", "BUI", "BUM", "BUR", "BURAPA", "BURT", "BVH",
    "BWG", "BWGCP", "BWN", "BXP", "CA", "CAM", "CAZ", "CBI", "CBL", "CBP", "CBT", "CCAP",
    "CCC", "CCCAP", "CCET", "CCT", "CDH", "CEI", "CENTEL", "CERC", "CF", "CFR", "CGH",
    "CGP", "CHB", "CHC", "CHG", "CHG", "CHO", "CHP", "CIFF", "CITY", "CK", "CKP", "CL",
    "CLP", "CM", "CMC", "CMR", "CMS", "CMSQ", "CN", "CNS", "CNTR", "CO", "COL", "COLW",
    "COM7", "COMM", "COP", "CPall", "CPAXT", "CPF", "CPFX", "CPG", "CPH", "CPHNW", "CPI",
    "CPICAP", "CPIF", "CPL", "CPNREIT", "CPR", "CPSE", "CPUW", "CPW", "CQ", "CR", "CRA",
    "CRC", "CRE", "CRES", "CRPT", "CRT", "CRW", "CS", "CSC", "CSCP", "CSL", "CSP", "CSR",
    "CSS", "CST", "CTE", "CTG", "CTM", "CTMI", "CTS", "CTW", "CUE", "CUBE", "CV", "CVT",
    "CWT", "CWUT", "DA", "DANCE", "DAP", "DAW", "DBD", "DEMCO", "DEXON", "DFC", "DFT",
    "DHAMRN", "DHN", "DIC", "DIF", "DINA", "DIP", "DISQ", "DJSE", "DKC", "DMC", "DMT",
    "DMTN", "DN", "DNP", "DNSE", "DOD", "DOHOME", "DOM", "DRACO", "DPORT", "DRCT", "DRICH",
    "DRT", "DRTN", "DRW", "DSIN", "DTCD", "DTCO", "DTC", "DTCAP", "DTECH", "DUL", "DUNE",
    "E", "EA", "EAT", "EASYNET", "ECF", "ECON", "ECRAN", "ECT", "ECTR", "EE", "EEC", "EECO",
    "EEPC", "EEU", "EGA", "EGCO", "EIDL", "EIREIT", "EIT", "EKH", "EKPC", "EKT", "ELEC",
    "ELEX", "ELITE", "EM", "EMCO", "EMS", "EMSO", "EMT", "ENA", "ENE", "ENG", "ENPT", "EON",
    "EP", "EPA", "EPCO", "EPLCO", "EPS", "ERE", "ERN", "ERW", "ES", "ESC", "ESCO", "ESL",
    "ESON", "ESRT", "ESTA", "ESTI", "ESTV", "ET", "ETA", "ETIME", "ETN", "ETR", "ETS",
    "EXIM", "EXIM", "FABER", "FABIF", "FABS", "FACE", "FAD", "FAIR", "FAME", "FAN", "FANCY",
    "FAP", "FAT", "FATCO", "FBN", "FE", "FENA", "FFC", "FFH", "FFI", "FIL", "FIMACAP", "FIN",
    "FINC", "FIP", "FIRE", "FIT", "FLA", "FLAMAX", "FLAP", "FLC", "FLE", "FLEE", "FLES", "FLT",
    "FN", "FNA", "FNANT", "FND", "FNG", "FNPT", "FNS", "FNSE", "FNSH", "FOI", "FOLK", "FONB",
    "FP", "FPA", "FPC", "FPVF", "FR", "FRAME", "FRD", "FREZT", "FRH", "FRI", "FRIL", "FS",
    "FSS", "FTE", "FTEFT", "FTHL", "FTKREIT", "FTREIT", "FTW", "FTWRT", "FTWTA", "FULLW",
    "FUN", "FUP", "FUS", "FUT", "FUTURE", "FV", "FVP", "G", "GA", "GAG", "GAL", "GAMCO",
    "GAMIN", "GAP", "GARIN", "GARTH", "GAS", "GASS", "GAT", "GATE", "GAUGH", "GBB", "GBX",
    "GC", "GCA", "GCH", "GCP", "GCQ", "GCURL", "GD", "GDC", "GDCI", "GDS", "GE", "GEE",
    "GEM", "GEMINC", "GETG", "GF", "GFC", "GFPT", "GG", "GGC", "GGM", "GGP", "GH", "GHC",
    "GHP", "GI", "GIC", "GICL", "GIG", "GILT", "GJAS", "GKH", "GKP", "GLAD", "GLAND", "GLC",
    "GLDREIT", "GLEX", "GLO", "GLOBAL", "GLOSS", "GLPG", "GLPI", "GLPQ", "GLPT", "GLTF",
    "GMCP", "GMM", "GMMAPT", "GMMOIL", "GMS", "GMSGF", "GMY", "GN", "GNEE", "GNPT", "GO",
    "GOB", "GOBX", "GOLD", "GOLF", "GOLFCAP", "GOLW", "GOR", "GOVE", "GPI", "GPF", "GPGC",
    "GPSC", "GQH", "GR", "GRACE", "GRAMMY", "GRANT", "GRAS", "GRASP", "GRAT", "GRB", "GRBCP",
    "GRC", "GRH", "GRIME", "GRIT", "GRIZ", "GRNCO", "GRU", "GRUCP", "GS", "GSAP", "GSB",
    "GSC", "GSCP", "GSD", "GSE", "GSETF", "GSFC", "GSFX", "GSFXW", "GSG", "GSGCP", "GSM",
    "GSMCP", "GSP", "GSPQ", "GSPT", "GSPTG", "GSPTW", "GT", "GTA", "GTCO", "GTE", "GTF",
    "GTFUND", "GTGCP", "GTL", "GTLCP", "GTS", "GTSE", "GUA", "GUAP", "GULF", "GULFCP",
    "GUM", "GV", "GVB", "GVC", "GVCCP", "GW", "GWC", "GWCCP", "GWFO", "GX", "GXC", "GY",
    "GYPSUM", "GZ", "GZCAP", "HA", "HAH", "HAINE", "HAP", "HARA", "HARE", "HART", "HAS",
    "HASIQ", "HAUTE", "HAW", "HAWAI", "HAY", "HAYFL", "HB", "HBL", "HC", "HCA", "HCAH",
    "HCJ", "HCP", "HCS", "HD", "HDA", "HDCI", "HDP", "HDT", "HDYCP", "HE", "HEAD", "HECK",
    "HEM", "HEMCO", "HEN", "HEP", "HERAIT", "HERA", "HERAS", "HES", "HETF", "HETH", "HF",
    "HFA", "HFC", "HFUND", "HG", "HGC", "HGH", "HGHO", "HGHP", "HGI", "HH", "HHC", "HHT",
    "HI", "HIAT", "HIC", "HICO", "HIDDEN", "HIGH", "HIGHN", "HIGHT", "HIM", "HINA", "HIP",
    "HIPB", "HIPO", "HIS", "HIST", "HITEC", "HJ", "HL", "HLM", "HLMCP", "HMC", "HMCP",
    "HMP", "HMPRO", "HMPPF", "HMS", "HMT", "HN", "HNC", "HNCAP", "HNR", "HNW", "HO", "HOC",
    "HOCP", "HONE", "HOP", "HOPG", "HOPN", "HOPE", "HOPP", "HOPPT", "HOPT", "HOT", "HOTAI",
    "HP", "HPCAP", "HPE", "HPET", "HPI", "HPICAP", "HPIPE", "HPT", "HR", "HRBIF", "HRC",
    "HRCP", "HRE", "HREIF", "HRN", "HRPT", "HRS", "HS", "HSCP", "HST", "HT", "HTCP", "HTE",
    "HTIF", "HTIS", "HTN", "HTNCP", "HTO", "HTS", "HTTF", "HTW", "HU", "HUB", "HUBBK", "HUM",
    "HUN", "HUNCH", "HUP", "HURT", "HURU", "HUSC", "HUSQ", "HUSTF", "HUT", "HV", "HVA", "HVT",
    "HW", "HWC", "HWCAP", "HWE", "HWIK", "HX", "HXM", "HYMF", "HYP", "HYT", "I", "IA", "IAH",
    "IAJF", "IB", "IBCH", "IBCL", "IBL", "IBON", "IBS", "IC", "ICAP", "ICE", "ICH", "ICHF",
    "ICP", "ICTI", "ID", "IDAG", "IDBF", "IDEJ", "IDF", "IDIT", "IDSE", "IDT", "IDTC", "IDTW",
    "IEC", "IECO", "IEG", "IES", "IEVER", "IF", "IFA", "IFAC", "IFAST", "IFBK", "IFC", "IFCP",
    "IFCT", "IFCW", "IFED", "IFEX", "IFHL", "IFI", "IFIF", "IFIL", "IFIS", "IFLA", "IFLIF",
    "IFM", "IFMIC", "IFPT", "IFT", "IFTF", "IFTH", "IG", "IGCC", "IGG", "IGGF", "IGH", "IGHF",
    "IGM", "IGMF", "IGPG", "IGPT", "IGSB", "IGT", "IGTF", "IH", "IHC", "IHCBF", "IHEQ", "IHF",
    "IHFBF", "IHHF", "IHP", "II", "IICA", "IIGF", "IIM", "IIMC", "IIN", "IIPT", "IISF", "IIT",
    "IJC", "IJH", "IK", "IKCO", "IKCV", "IKT", "IL", "ILM", "ILN", "ILS", "IM", "IMEX", "IMH",
    "IMICAP", "IMIF", "IMPA", "IMPF", "IMS", "IMSF", "IMT", "IMTF", "IN", "INA", "INAG", "INAI",
    "INB", "INBF", "INCAP", "INCF", "INCO", "INCT", "IND", "INDRF", "INET", "INF", "INFRA",
    "ING", "INGF", "INH", "INIAP", "INL", "INMC", "INMF", "INNO", "INNOV", "INOV", "INOX",
    "INP", "INPHI", "INPT", "INR", "INRI", "INROM", "INS", "INSF", "INSQ", "INSURE", "INT",
    "INTBF", "INTC", "INTER", "INTI", "INTIF", "INTL", "INTUCH", "INV", "INVC", "INVF",
    "INVP", "INVQ", "IO", "IOC", "IOD", "IODIF", "IOIA", "IOM", "ION", "IONIF", "IOP", "IOR",
    "IORS", "IOS", "IOTP", "IP", "IPA", "IPAC", "IPACP", "IPAP", "IPAS", "IPAT", "IPC", "IPCAP",
    "IPCH", "IPCP", "IPD", "IPDF", "IPEG", "IPEM", "IPF", "IPFBF", "IPFC", "IPFD", "IPFE",
    "IPFF", "IPFG", "IPFH", "IPFIF", "IPFJ", "IPFM", "IPFN", "IPFP", "IPFQ", "IPFR", "IPFS",
    "IPFT", "IPFU", "IPFW", "IPFX", "IPFZ", "IPG", "IPGC", "IPH", "IPHC", "IPHA", "IPHF",
    "IPHIF", "IPHN", "IPHP", "IPHR", "IPHS", "IPHTT", "IPI", "IPIC", "IPIIF", "IPIL", "IPJ",
    "IPJC", "IPK", "IPKC", "IPL", "IPLC", "IPLCP", "IPM", "IPMF", "IPN", "IPNC", "IPO", "IPOC",
    "IPOF", "IPOG", "IPOH", "IPOI", "IPOP", "IPOR", "IPOS", "IPOT", "IPP", "IPPC", "IPPF",
    "IPQ", "IPQC", "IPR", "IPRC", "IPRF", "IPRIF", "IPRIL", "IPRO", "IPRQ", "IPRT", "IPRU",
    "IPRY", "IPS", "IPSC", "IPSCP", "IPSF", "IPSP", "IPSQ", "IPST", "IPT", "IPTC", "IPTCP",
    "IPTF", "IPTI", "IPTN", "IPU", "IPUC", "IPUF", "IPUI", "IPUL", "IPUN", "IPUP", "IPUQ",
    "IPUR", "IPUS", "IPUT", "IPUU", "IPV", "IPVC", "IPVF", "IPVI", "IPVP", "IPVR", "IPVS",
    "IPVT", "IPW", "IPWC", "IPWF", "IPWI", "IPWP", "IPWS", "IPWU", "IPX", "IPXC", "IPXF",
    "IPXI", "IPXP", "IPXS", "IPXU", "IPY", "IPYC", "IPYF", "IPYI", "IPYP", "IPYS", "IPYU",
    "IPZ", "IPZC", "IPZF", "IPZI", "IPZP", "IPZS", "IPZU", "IQ", "IQIF", "IR", "IRC", "IRCAP",
    "IRCP", "IRCT", "IRD", "IRE", "IREI", "IREIT", "IREM", "IREQ", "IRES", "IRF", "IRFC",
    "IRFIF", "IRFP", "IRFT", "IRFY", "IRG", "IRGC", "IRGCP", "IRGF", "IRGP", "IRGS", "IRGT",
    "IRH", "IRHC", "IRHCP", "IRHF", "IRHP", "IRHS", "IRHT", "IRI", "IRIC", "IRICP", "IRIF",
    "IRIP", "IRIS", "IRIT", "IRJ", "IRJC", "IRJCP", "IRJF", "IRJP", "IRJS", "IRJT", "IRK",
    "IRKC", "IRKCP", "IRKF", "IRKP", "IRKS", "IRKT", "IRL", "IRLC", "IRLCP", "IRLF", "IRLP",
    "IRLS", "IRLT", "IRM", "IRMC", "IRMCP", "IRMF", "IRMP", "IRMS", "IRMT", "IRN", "IRNC",
    "IRNCP", "IRNF", "IRNP", "IRNS", "IRNT", "IRO", "IROC", "IROCP", "IROF", "IROP", "IROS",
    "IROT", "IRP", "IRPC", "IRPCP", "IRPF", "IRPP", "IRPS", "IRPT", "IRQ", "IRQC", "IRQCP",
    "IRQF", "IRQP", "IRQS", "IRQT", "IRR", "IRRC", "IRRCP", "IRRF", "IRRP", "IRRS", "IRRT",
    "IRS", "IRSC", "IRSCP", "IRSF", "IRSP", "IRSS", "IRST", "IRT", "IRTC", "IRTCP", "IRTF",
    "IRTP", "IRTS", "IRTT", "IRU", "IRUC", "IRUCP", "IRUF", "IRUP", "IRUS", "IRUT", "IRV",
    "IRVC", "IRVCP", "IRVF", "IRVP", "IRVS", "IRVT", "IRW", "IRWC", "IRWCP", "IRWF", "IRWP",
    "IRWS", "IRWT", "IRX", "IRXC", "IRXCP", "IRXF", "IRXP", "IRXS", "IRXT", "IRY", "IRYC",
    "IRYCP", "IRYF", "IRYP", "IRYS", "IRYT", "IRZ", "IRZC", "IRZCP", "IRZF", "IRZP", "IRZS",
    "IRZT", "IS", "ISC", "ISCP", "ISD", "ISDF", "ISE", "ISEF", "ISEH", "ISEP", "ISES", "ISET",
    "ISF", "ISFBK", "ISFC", "ISFCP", "ISFD", "ISFDF", "ISFEI", "ISFEP", "ISFES", "ISFET",
    "ISFH", "ISFHF", "ISFHP", "ISFHS", "ISFHT", "ISFIC", "ISFIF", "ISFIP", "ISFIS", "ISFIT",
    "ISFJ", "ISFJC", "ISFJF", "ISFJP", "ISFJS", "ISFJT", "ISFK", "ISFKC", "ISFKF", "ISFKP",
    "ISFKS", "ISFKT", "ISFL", "ISFLC", "ISFLF", "ISFLP", "ISFLS", "ISFLT", "ISFM", "ISFMC",
    "ISFMF", "ISFMP", "ISFMS", "ISFMT", "ISFN", "ISFNC", "ISFNF", "ISFNP", "ISFNS", "ISFNT",
    "ISFP", "ISFPC", "ISFPF", "ISFPP", "ISFPS", "ISFPT", "ISFQ", "ISFQC", "ISFQF", "ISFQP",
    "ISFQS", "ISFQT", "ISFR", "ISFRC", "ISFRF", "ISFRP", "ISFRS", "ISFRT", "ISFS", "ISFSC",
    "ISFSF", "ISFSP", "ISFSS", "ISFST", "ISFT", "ISFTC", "ISFTF", "ISFTP", "ISFTS", "ISFTT",
    "ISFU", "ISFUC", "ISFUF", "ISFUP", "ISFUS", "ISFUT", "ISFV", "ISFVC", "ISFVF", "ISFVP",
    "ISFVS", "ISFVT", "ISFW", "ISFWC", "ISFWF", "ISFWP", "ISFWS", "ISFWT", "ISFX", "ISFXC",
    "ISFXF", "ISFXP", "ISFXS", "ISFXT", "ISFY", "ISFYC", "ISFYF", "ISFYP", "ISFYS", "ISFYT",
    "ISFZ", "ISFZC", "ISFZF", "ISFZP", "ISFZS", "ISFZT", "ISG", "ISGC", "ISGCP", "ISGF",
    "ISGP", "ISGS", "ISGT", "ISH", "ISHC", "ISHCP", "ISHF", "ISHP", "ISHS", "ISHT", "ISI",
    "ISIC", "ISICP", "ISIF", "ISIP", "ISIS", "ISIT", "ISJ", "ISJC", "ISJCP", "ISJF", "ISJP",
    "ISJS", "ISJT", "ISK", "ISKC", "ISKCP", "ISKF", "ISKP", "ISKS", "ISKT", "ISL", "ISLC",
    "ISLCP", "ISLF", "ISLP", "ISLS", "ISLT", "ISM", "ISMC", "ISMCP", "ISMF", "ISMP", "ISMS",
    "ISMT", "ISN", "ISNC", "ISNCP", "ISNF", "ISNP", "ISNS", "ISNT", "ISO", "ISOC", "ISOCP",
    "ISOF", "ISOP", "ISOS", "ISOT", "ISP", "ISPC", "ISPCP", "ISPF", "ISPP", "ISPS", "ISPT",
    "ISQ", "ISQC", "ISQCP", "ISQF", "ISQP", "ISQS", "ISQT", "ISR", "ISRC", "ISRCP", "ISRF",
    "ISRP", "ISRS", "ISRT", "ISS", "ISSC", "ISSCP", "ISSF", "ISSP", "ISSS", "ISST", "IST",
    "ISTC", "ISTCP", "ISTF", "ISTP", "ISTS", "ISTT", "ISU", "ISUC", "ISUCP", "ISUF", "ISUP",
    "ISUS", "ISUT", "ISV", "ISVC", "ISVCP", "ISVF", "ISVP", "ISVS", "ISVT", "ISW", "ISWC",
    "ISWCP", "ISWF", "ISWP", "ISWS", "ISWT", "ISX", "ISXC", "ISXCP", "ISXF", "ISXP", "ISXS",
    "ISXT", "ISY", "ISYC", "ISYCP", "ISYF", "ISYP", "ISYS", "ISYT", "ISZ", "ISZC", "ISZCP",
    "ISZF", "ISZP", "ISZS", "ISZT", "IT", "ITA", "ITAC", "ITACAP", "ITAF", "ITAP", "ITAS",
    "ITAT", "ITB", "ITBC", "ITBCP", "ITBF", "ITBP", "ITBS", "ITBT", "ITC", "ITCC", "ITCCP",
    "ITCF", "ITCP", "ITCS", "ITCT", "ITD", "ITDC", "ITDCP", "ITDF", "ITDP", "ITDS", "ITDT",
    "ITE", "ITEC", "ITECP", "ITEF", "ITEP", "ITES", "ITET", "ITF", "ITFC", "ITFCP", "ITFF",
    "ITFP", "ITFS", "ITFT", "ITG", "ITGC", "ITGCP", "ITGF", "ITGP", "ITGS", "ITGT", "ITH",
    "ITHC", "ITHCP", "ITHF", "ITHP", "ITHS", "ITHT", "ITI", "ITIC", "ITICP", "ITIF", "ITIP",
    "ITIS", "ITIT", "ITJ", "ITJC", "ITJCP", "ITJF", "ITJP", "ITJS", "ITJT", "ITK", "ITKC",
    "ITKCP", "ITKF", "ITKP", "ITKS", "ITKT", "ITL", "ITLC", "ITLCP", "ITLF", "ITLP", "ITLS",
    "ITLT", "ITM", "ITMC", "ITMCP", "ITMF", "ITMP", "ITMS", "ITMT", "ITN", "ITNC", "ITNCP",
    "ITNF", "ITNP", "ITNS", "ITNT", "ITO", "ITOC", "ITOCP", "ITOF", "ITOP", "ITOS", "ITOT",
    "ITP", "ITPC", "ITPCP", "ITPF", "ITPP", "ITPS", "ITPT", "ITQ", "ITQC", "ITQCP", "ITQF",
    "ITQP", "ITQS", "ITQT", "ITR", "ITRC", "ITRCP", "ITRF", "ITRP", "ITRS", "ITRT", "ITS",
    "ITSC", "ITSCP", "ITSF", "ITSP", "ITSS", "ITST", "ITT", "ITTC", "ITTCP", "ITTF", "ITTP",
    "ITTS", "ITTT", "ITU", "ITUC", "ITUCP", "ITUF", "ITUP", "ITUS", "ITUT", "ITV", "ITVC",
    "ITVCP", "ITVF", "ITVP", "ITVS", "ITVT", "ITW", "ITWC", "ITWCP", "ITWF", "ITWP", "ITWS",
    "ITWT", "ITX", "ITXC", "ITXCP", "ITXF", "ITXP", "ITXS", "ITXT", "ITY", "ITYC", "ITYCP",
    "ITYF", "ITYP", "ITYS", "ITYT", "ITZ", "ITZC", "ITZCP", "ITZF", "ITZP", "ITZS", "ITZT",
    "IU", "IUAN", "IUAP", "IUAS", "IUAT", "IUC", "IUCA", "IUCAP", "IUCF", "IUCP", "IUCS",
    "IUCT", "IUD", "IUDA", "IUDAP", "IUDF", "IUDP", "IUDS", "IUDT", "IUE", "IUEA", "IUEAP",
    "IUEF", "IUEP", "IUES", "IUET", "IUF", "IUFA", "IUFAP", "IUFF", "IUFP", "IUFS", "IUFT",
    "IUG", "IUGA", "IUGAP", "IUGF", "IUGP", "IUGS", "IUGT", "IUH", "IUHA", "IUHAP", "IUHF",
    "IUHP", "IUHS", "IUHT", "IUI", "IUIA", "IUIAP", "IUIF", "IUIP", "IUIS", "IUIT", "IUJ",
    "IUJA", "IUJAP", "IUJF", "IUJP", "IUJS", "IUJT", "IUK", "IUKA", "IUKAP", "IUKF", "IUKP",
    "IUKS", "IUKT", "IUL", "IULA", "IULAP", "IULF", "IULP", "IULS", "IULT", "IUM", "IUMA",
    "IUMAP", "IUMF", "IUMP", "IUMAS", "IUMT", "IUN", "IUNA", "IUNAP", "IUNF", "IUNP", "IUNS",
    "IUNT", "IUO", "IUOA", "IUOAP", "IUOF", "IUOP", "IUOS", "IUOT", "IUP", "IUPA", "IUPAP",
    "IUPF", "IUPP", "IUPS", "IUPT", "IUQ", "IUQA", "IUQAP", "IUQF", "IUQP", "IUQS", "IUQT",
    "IUR", "IURA", "IURAP", "IURF", "IURP", "IURS", "IURT", "IUS", "IUSA", "IUSAP", "IUSF",
    "IUSP", "IUSS", "IUST", "IUT", "IUTA", "IUTAP", "IUTF", "IUTP", "IUTS", "IUTT", "IUU",
    "IUUA", "IUUAP", "IUUF", "IUUP", "IUUS", "IUUT", "IUV", "IUVA", "IUVAP", "IUVF", "IUVP",
    "IUVS", "IUVT", "IUW", "IUWA", "IUWAP", "IUWF", "IUWP", "IUWS", "IUWT", "IUX", "IUXA",
    "IUXAP", "IUXF", "IUXP", "IUXS", "IUXT", "IUY", "IUYA", "IUYAP", "IUYF", "IUYP", "IUYS",
    "IUYT", "IUZ", "IUZA", "IUZAP", "IUZF", "IUZP", "IUZS", "IUZT", "IV", "IVA", "IVAC",
    "IVACP", "IVAF", "IVAP", "IVAS", "IVAT", "IVB", "IVBC", "IVBCP", "IVBF", "IVBP", "IVBS",
    "IVBT", "IVC", "IVCC", "IVCCP", "IVCF", "IVCP", "IVCS", "IVCT", "IVD", "IVDC", "IVDCP",
    "IVDF", "IVDP", "IVDS", "IVDT", "IVE", "IVEC", "IVECP", "IVEF", "IVEP", "IVES", "IVET",
    "IVF", "IVFC", "IVFCP", "IVFF", "IVFP", "IVFS", "IVFT", "IVG", "IVGC", "IVGCP", "IVGF",
    "IVGP", "IVGS", "IVGT", "IVH", "IVHC", "IVHCP", "IVHF", "IVHP", "IVHS", "IVHT", "IVI",
    "IVIC", "IVICP", "IVIF", "IVIP", "IVIS", "IVIT", "IVJ", "IVJC", "IVJCP", "IVJF", "IVJP",
    "IVJS", "IVJT", "IVK", "IVKC", "IVKCP", "IVKF", "IVKP", "IVKS", "IVKT", "IVL", "IVLC",
    "IVLCP", "IVLF", "IVLP", "IVLS", "IVLT", "IVM", "IVMC", "IVMCP", "IVMF", "IVMP", "IVMS",
    "IVMT", "IVN", "IVNC", "IVNCP", "IVNF", "IVNP", "IVNS", "IVNT", "IVO", "IVOC", "IVOCP",
    "IVOF", "IVOP", "IVOS", "IVOT", "IVP", "IVPC", "IVPCP", "IVPF", "IVPP", "IVPS", "IVPT",
    "IVQ", "IVQC", "IVQCP", "IVQF", "IVQP", "IVQS", "IVQT", "IVR", "IVRC", "IVRCP", "IVRF",
    "IVRP", "IVRS", "IVRT", "IVS", "IVSC", "IVSCP", "IVSF", "IVSP", "IVSS", "IVST", "IVT",
    "IVTC", "IVTCP", "IVTF", "IVTP", "IVTS", "IVTT", "IVU", "IVUC", "IVUCP", "IVUF", "IVUP",
    "IVUS", "IVUT", "IVV", "IVVC", "IVVCP", "IVVF", "IVVP", "IVVS", "IVVT", "IVW", "IVWC",
    "IVWCP", "IVWF", "IVWP", "IVWS", "IVWT", "IVX", "IVXC", "IVXCP", "IVXF", "IVXP", "IVXS",
    "IVXT", "IVY", "IVYC", "IVYCP", "IVYF", "IVYP", "IVYS", "IVYT", "IVZ", "IVZC", "IVZCP",
    "IVZF", "IVZP", "IVZS", "IVZT", "IW", "IWA", "IWAC", "IWACP", "IWAF", "IWAP", "IWAS",
    "IWAT", "IWB", "IWBC", "IWBCP", "IWBF", "IWBP", "IWBS", "IWBT", "IWC", "IWCC", "IWCCP",
    "IWCF", "IWCP", "IWCS", "IWCT", "IWD", "IWDC", "IWDCP", "IWDF", "IWDP", "IWDS", "IWDT",
    "IWE", "IWEC", "IWECP", "IWEF", "IWEP", "IWES", "IWET", "IWF", "IWFC", "IWFCP", "IWFF",
    "IWFP", "IWFS", "IWFT", "IWG", "IWGC", "IWGCP", "IWGF", "IWGP", "IWGS", "IWGT", "IWH",
    "IWHC", "IWHCP", "IWHF", "IWHP", "IWHS", "IWHT", "IWI", "IWIC", "IWICP", "IWIF", "IWIP",
    "IWIS", "IWIT", "IWJ", "IWJC", "IWJCP", "IWJF", "IWJP", "IWJS", "IWJT", "IWK", "IWKC",
    "IWKCP", "IWKF", "IWKP", "IWKS", "IWKT", "IWL", "IWLC", "IWLCP", "IWLF", "IWLP", "IWLS",
    "IWLT", "IWM", "IWMC", "IWMCP", "IWMF", "IWMP", "IWMS", "IWMT", "IWN", "IWNC", "IWNCP",
    "IWNF", "IWNP", "IWNS", "IWNT", "IWO", "IWOC", "IWOCP", "IWOF", "IWOP", "IWOS", "IWOT",
    "IWP", "IWPC", "IWPCP", "IWPF", "IWPP", "IWPS", "IWPT", "IWQ", "IWQC", "IWQCP", "IWQF",
    "IWQP", "IWQS", "IWQT", "IWR", "IWRC", "IWRCP", "IWRF", "IWRP", "IWRS", "IWRT", "IWS",
    "IWSC", "IWSCP", "IWSF", "IWSP", "IWSS", "IWST", "IWT", "IWTC", "IWTCP", "IWTF", "IWTP",
    "IWTS", "IWTT", "IWU", "IWUC", "IWUCP", "IWUF", "IWUP", "IWUS", "IWUT", "IWV", "IWVC",
    "IWVCP", "IWVF", "IWVP", "IWVS", "IWVT", "IWW", "IWWC", "IWWCP", "IWWF", "IWWP", "IWWS",
    "IWWT", "IWX", "IWXC", "IWXCP", "IWXF", "IWXP", "IWXS", "IWXT", "IWY", "IWYC", "IWYCP",
    "IWYF", "IWYP", "IWYS", "IWYT", "IWZ", "IWZC", "IWZCP", "IWZF", "IWZP", "IWZS", "IWZT",
    "IX", "IXA", "IXAC", "IXACP", "IXAF", "IXAP", "IXAS", "IXAT", "IXB", "IXBC", "IXBCP",
    "IXBF", "IXBP", "IXBS", "IXBT", "IXC", "IXCC", "IXCCP", "IXCF", "IXCP", "IXCS", "IXCT",
    "IXD", "IXDC", "IXDCP", "IXDF", "IXDP", "IXDS", "IXDT", "IXE", "IXEC", "IXECP", "IXEF",
    "IXEP", "IXES", "IXET", "IXF", "IXFC", "IXFCP", "IXFF", "IXFP", "IXFS", "IXFT", "IXG",
    "IXGC", "IXGCP", "IXGF", "IXGP", "IXGS", "IXGT", "IXH", "IXHC", "IXHCP", "IXHF", "IXHP",
    "IXHS", "IXHT", "IXI", "IXIC", "IXICP", "IXIF", "IXIP", "IXIS", "IXIT", "IXJ", "IXJC",
    "IXJCP", "IXJF", "IXJP", "IXJS", "IXJT", "IXK", "IXKC", "IXKCP", "IXKF", "IXKP", "IXKS",
    "IXKT", "IXL", "IXLC", "IXLCP", "IXLF", "IXLP", "IXLS", "IXLT", "IXM", "IXMC", "IXMCP",
    "IXMF", "IXMP", "IXMS", "IXMT", "IXN", "IXNC", "IXNCP", "IXNF", "IXNP", "IXNS", "IXNT",
    "IXO", "IXOC", "IXOCP", "IXOF", "IXOP", "IXOS", "IXOT", "IXP", "IXPC", "IXPCP", "IXPF",
    "IXPP", "IXPS", "IXPT", "IXQ", "IXQC", "IXQCP", "IXQF", "IXQP", "IXQS", "IXQT", "IXR",
    "IXRC", "IXRCP", "IXRF", "IXRP", "IXRS", "IXRT", "IXS", "IXSC", "IXSCP", "IXSF", "IXSP",
    "IXSS", "IXST", "IXT", "IXTC", "IXTCP", "IXTF", "IXTP", "IXTS", "IXTT", "IXU", "IXUC",
    "IXUCP", "IXUF", "IXUP", "IXUS", "IXUT", "IXV", "IXVC", "IXVCP", "IXVF", "IXVP", "IXVS",
    "IXVT", "IXW", "IXWC", "IXWCP", "IXWF", "IXWP", "IXWS", "IXWT", "IXX", "IXXC", "IXXCP",
    "IXXF", "IXXP", "IXXS", "IXXT", "IXY", "IXYC", "IXYCP", "IXYF", "IXYP", "IXYS", "IXYT",
    "IXZ", "IXZC", "IXZCP", "IXZF", "IXZP", "IXZS", "IXZT", "IY", "IYA", "IYAC", "IYACP",
    "IYAF", "IYAP", "IYAS", "IYAT", "IYB", "IYBC", "IYBCP", "IYBF", "IYBP", "IYBS", "IYBT",
    "IYC", "IYCC", "IYCCP", "IYCF", "IYCP", "IYCS", "IYCT", "IYD", "IYDC", "IYDCP", "IYDF",
    "IYDP", "IYDS", "IYDT", "IYE", "IYEC", "IYECP", "IYEF", "IYEP", "IYES", "IYET", "IYF",
    "IYFC", "IYFCP", "IYFF", "IYFP", "IYFS", "IYFT", "IYG", "IYGC", "IYGCP", "IYGF", "IYGP",
    "IYGS", "IYGT", "IYH", "IYHC", "IYHCP", "IYHF", "IYHP", "IYHS", "IYHT", "IYI", "IYIC",
    "IYICP", "IYIF", "IYIP", "IYIS", "IYIT", "IYJ", "IYJC", "IYJCP", "IYJF", "IYJP", "IYJS",
    "IYJT", "IYK", "IYKC", "IYKCP", "IYKF", "IYKP", "IYKS", "IYKT", "IYL", "IYLC", "IYLCP",
    "IYLF", "IYLP", "IYLS", "IYLT", "IYM", "IYMC", "IYMCP", "IYMF", "IYMP", "IYMS", "IYMT",
    "IYN", "IYNC", "IYNCP", "IYNF", "IYNP", "IYNS", "IYNT", "IYO", "IYOC", "IYOCP", "IYOF",
    "IYOP", "IYOS", "IYOT", "IYP", "IYPC", "IYPCP", "IYPF", "IYPP", "IYPS", "IYPT", "IYQ",
    "IYQC", "IYQCP", "IYQF", "IYQP", "IYQS", "IYQT", "IYR", "IYRC", "IYRCP", "IYRF", "IYRP",
    "IYRS", "IYRT", "IYS", "IYSC", "IYSCP", "IYSF", "IYSP", "IYSS", "IYST", "IYT", "IYTC",
    "IYTCP", "IYTF", "IYTP", "IYTS", "IYTT", "IYU", "IYUC", "IYUCP", "IYUF", "IYUP", "IYUS",
    "IYUT", "IYV", "IYVC", "IYVCP", "IYVF", "IYVP", "IYVS", "IYVT", "IYW", "IYWC", "IYWCP",
    "IYWF", "IYWP", "IYWS", "IYWT", "IYX", "IYXC", "IYXCP", "IYXF", "IYXP", "IYXS", "IYXT",
    "IYY", "IYYC", "IYYCP", "IYYF", "IYYP", "IYYS", "IYYT", "IYZ", "IYZC", "IYZCP", "IYZF",
    "IYZP", "IYZS", "IYZT", "IZ", "IZA", "IZAC", "IZACP", "IZAF", "IZAP", "IZAS", "IZAT",
    "IZB", "IZBC", "IZBCP", "IZBF", "IZBP", "IZBS", "IZBT", "IZC", "IZCC", "IZCCP", "IZCF",
    "IZCP", "IZCS", "IZCT", "IZD", "IZDC", "IZDCP", "IZDF", "IZDP", "IZDS", "IZDT", "IZE",
    "IZEC", "IZECP", "IZEF", "IZEP", "IZES", "IZET", "IZF", "IZFC", "IZFCP", "IZFF", "IZFP",
    "IZFS", "IZFT", "IZG", "IZGC", "IZGCP", "IZGF", "IZGP", "IZGS", "IZGT", "IZH", "IZHC",
    "IZHCP", "IZHF", "IZHP", "IZHS", "IZHT", "IZI", "IZIC", "IZICP", "IZIF", "IZIP", "IZIS",
    "IZIT", "IZJ", "IZJC", "IZJCP", "IZJF", "IZJP", "IZJS", "IZJT", "IZK", "IZKC", "IZKCP",
    "IZKF", "IZKP", "IZKS", "IZKT", "IZL", "IZLC", "IZLCP", "IZLF", "IZLP", "IZLS", "IZLT",
    "IZM", "IZMC", "IZMCP", "IZMF", "IZMP", "IZMS", "IZMT", "IZN", "IZNC", "IZNCP", "IZNF",
    "IZNP", "IZNS", "IZNT", "IZO", "IZOC", "IZOCP", "IZOF", "IZOP", "IZOS", "IZOT", "IZP",
    "IZPC", "IZPCP", "IZPF", "IZPP", "IZPS", "IZPT", "IZQ", "IZQC", "IZQCP", "IZQF", "IZQP",
    "IZQS", "IZQT", "IZR", "IZRC", "IZRCP", "IZRF", "IZRP", "IZRS", "IZRT", "IZS", "IZSC",
    "IZSCP", "IZSF", "IZSP", "IZSS", "IZST", "IZT", "IZTC", "IZTCP", "IZTF", "IZTP", "IZTS",
    "IZTT", "IZU", "IZUC", "IZUCP", "IZUF", "IZUP", "IZUS", "IZUT", "IZV", "IZVC", "IZVCP",
    "IZVF", "IZVP", "IZVS", "IZVT", "IZW", "IZWC", "IZWCP", "IZWF", "IZWP", "IZWS", "IZWT",
    "IZX", "IZXC", "IZXCP", "IZXF", "IZXP", "IZXS", "IZXT", "IZY", "IZYC", "IZYCP", "IZYF",
    "IZYP", "IZYS", "IZYT", "IZZ", "IZZC", "IZZCP", "IZZF", "IZZP", "IZZS", "IZZT", "J",
    "JA", "JAAT", "JAB", "JACK", "JACOBY", "JADE", "JADECP", "JAFI", "JAG", "JAI", "JAIL",
    "JAK", "JALIF", "JAM", "JAMIF", "JAN", "JANET", "JAP", "JAPAN", "JAR", "JARD", "JARIF",
    "JARI", "JARIL", "JARN", "JAROT", "JARW", "JAS", "JASAS", "JASIF", "JASN", "JASPT",
    "JASW", "JAT", "JATA", "JATC", "JATCH", "JATE", "JATG", "JATH", "JATIF", "JATIP", "JATL",
    "JATP", "JATR", "JATS", "JATT", "JATW", "JAV", "JAVA", "JAW", "JAX", "JAY", "JAYF", "JB",
    "JBA", "JBAC", "JBAF", "JBAP", "JBAS", "JBAT", "JBB", "JBBC", "JBBF", "JBBP", "JBBS",
    "JBBT", "JBC", "JBCC", "JBCF", "JBCP", "JBCS", "JBCT", "JBD", "JBDC", "JBDF", "JBDP",
    "JBDS", "JBDT", "JBE", "JBEC", "JBEF", "JBEP", "JBES", "JBET", "JBF", "JBFC", "JBFF",
    "JBFP", "JBFS", "JBFT", "JBG", "JBGC", "JBGF", "JBGP", "JBGS", "JBGT", "JBH", "JBHC",
    "JBHF", "JBHP", "JBHS", "JBHT", "JBI", "JBIC", "JBIF", "JBIP", "JBIS", "JBIT", "JBJ",
    "JBJC", "JBJF", "JBJP", "JBJS", "JBJT", "JBK", "JBKC", "JBKF", "JBKP", "JBKS", "JBKT",
    "JBL", "JBLC", "JBLF", "JBLP", "JBLS", "JBLT", "JBM", "JBMC", "JBMF", "JBMP", "JBMS",
    "JBMT", "JBN", "JBNC", "JBNF", "JBNP", "JBNS", "JBNT", "JBO", "JBOC", "JBOF", "JBOP",
    "JBOS", "JBOT", "JBP", "JBPC", "JBPF", "JBPP", "JBPS", "JBPT", "JBQ", "JBQC", "JBQF",
    "JBQP", "JBQS", "JBQT", "JBR", "JBRC", "JBRF", "JBRP", "JBRS", "JBRT", "JBS", "JBSC",
    "JBSF", "JBSP", "JBSS", "JBST", "JBT", "JBTC", "JBTF", "JBTP", "JBTS", "JBTT", "JBU",
    "JBUC", "JBUF", "JBUP", "JBUS", "JBUT", "JBV", "JBVC", "JBVF", "JBVP", "JBVS", "JBVT",
    "JBW", "JBWC", "JBWF", "JBWP", "JBWS", "JBWT", "JBX", "JBXC", "JBXF", "JBXP", "JBXS",
    "JBXT", "JBY", "JBYC", "JBYF", "JBYP", "JBYS", "JBYT", "JBZ", "JBZC", "JBZF", "JBZP",
    "JBZS", "JBZT", "JC", "JCA", "JCAC", "JCAF", "JCAP", "JCAS", "JCAT", "JCB", "JCBC",
    "JCBF", "JCBP", "JCBS", "JCBT", "JCC", "JCCC", "JCCCAP", "JCCCW", "JCCF", "JCCP", "JCCS",
    "JCCT", "JCD", "JCDC", "JCDF", "JCDP", "JCDS", "JCDT", "JCE", "JCEC", "JCEF", "JCEP",
    "JCES", "JCET", "JCF", "JCFC", "JCFF", "JCFP", "JCFS", "JCFT", "JCG", "JCGC", "JCGF",
    "JCGP", "JCGS", "JCGT", "JCH", "JCHC", "JCHF", "JCHP", "JCHS", "JCHT", "JCI", "JCIC",
    "JCIF", "JCIP", "JCIS", "JCIT", "JCJ", "JCJC", "JCJF", "JCJP", "JCJS", "JCJT", "JCK",
    "JCKC", "JCKF", "JCKP", "JCKS", "JCKT", "JCL", "JCLC", "JCLF", "JCLP", "JCLS", "JCLT",
    "JCM", "JCMC", "JCMF", "JCMP", "JCMS", "JCMT", "JCN", "JCNC", "JCNF", "JCNP", "JCNS",
    "JCNT", "JCO", "JCOC", "JCOF", "JCOP", "JCOS", "JCOT", "JCP", "JCPC", "JCPF", "JCPP",
    "JCPS", "JCPT", "JCQ", "JCQC", "JCQF", "JCQP", "JCQS", "JCQT", "JCR", "JCRC", "JCRF",
    "JCRP", "JCRS", "JCRT", "JCS", "JCSC", "JCSF", "JCSP", "JCSS", "JCST", "JCT", "JCTC",
    "JCTF", "JCTP", "JCTS", "JCTT", "JCU", "JCUC", "JCUF", "JCUP", "JCUS", "JCUT", "JCV",
    "JCVC", "JCVF", "JCVP", "JCVS", "JCVT", "JCW", "JCWC", "JCWF", "JCWP", "JCWS", "JCWT",
    "JCX", "JCXC", "JCXF", "JCXP", "JCXS", "JCXT", "JCY", "JCYC", "JCYF", "JCYP", "JCYS",
    "JCYT", "JCZ", "JCZC", "JCZF", "JCZP", "JCZS", "JCZT", "JD", "JDA", "JDAC", "JDAF",
    "JDAP", "JDAS", "JDAT", "JDB", "JDBC", "JDBF", "JDBP", "JDBS", "JDBC", "JDC", "JDCC",
    "JDCF", "JDCP", "JDCS", "JDCT", "JDD", "JDDC", "JDDF", "JDDP", "JDDS", "JDDT", "JDE",
    "JDEC", "JDEF", "JDEP", "JDES", "JDET", "JDF", "JDFC", "JDFF", "JDFP", "JDFS", "JDFT",
    "JDG", "JDGC", "JDGF", "JDGP", "JDGS", "JDGT", "JDH", "JDHC", "JDHF", "JDHP", "JDHS",
    "JDHT", "JDI", "JDIC", "JDIF", "JDIP", "JDIS", "JDIT", "JDJ", "JDJC", "JDJF", "JDJP",
    "JDJS", "JDJT", "JDK", "JDKC", "JDKF", "JDKP", "JDKS", "JDKT", "JDL", "JDLC", "JDLF",
    "JDLP", "JDLS", "JDLT", "JDM", "JDMC", "JDMF", "JDMP", "JDMS", "JDMT", "JDN", "JDNC",
    "JDNF", "JDNP", "JDNS", "JDNT", "JDO", "JDOC", "JDOF", "JDOP", "JDOS", "JDOT", "JDP",
    "JDPC", "JDPF", "JDPP", "JDPS", "JDPT", "JDQ", "JDQC", "JDQF", "JDQP", "JDQS", "JDQT",
    "JDR", "JDRC", "JDRF", "JDRP", "JDRS", "JDRT", "JDS", "JDSC", "JDSF", "JDSP", "JDSS",
    "JDST", "JDT", "JDTC", "JDTF", "JDTP", "JDTS", "JDTT", "JDU", "JDUC", "JDUF", "JDUP",
    "JDUS", "JDUT", "JDV", "JDVC", "JDVF", "JDVP", "JDVS", "JDVT", "JDW", "JDWC", "JDWF",
    "JDWP", "JDWS", "JDWT", "JDX", "JDXC", "JDXF", "JDXP", "JDXS", "JDXT", "JDY", "JDYC",
    "JDYF", "JDYP", "JDYS", "JDYT", "JDZ", "JDZC", "JDZF", "JDZP", "JDZS", "JDZT", "JE",
    "JEA", "JEAC", "JEAF", "JEAP", "JEAS", "JEAT", "JEB", "JEBC", "JEBF", "JEBP", "JEBS",
    "JEBT", "JEC", "JECC", "JECF", "JECP", "JECS", "JECT", "JED", "JEDC", "JEDF", "JEDP",
    "JEDS", "JEDT", "JEE", "JEEC", "JEEF", "JEEP", "JEES", "JEET", "JEF", "JEFC", "JEFF",
    "JEFP", "JEFS", "JEFT", "JEG", "JEGC", "JEGF", "JEGP", "JEGS", "JEGT", "JEH", "JEHC",
    "JEHF", "JEHP", "JEHS", "JEHT", "JEI", "JEIC", "JEIF", "JEIP", "JEIS", "JEIT", "JEJ",
    "JEJC", "JEJF", "JEJP", "JEJS", "JEJT", "JEK", "JEKC", "JEKF", "JEKP", "JEKS", "JEKT",
    "JEL", "JELC", "JELF", "JELP", "JELS", "JELT", "JEM", "JEMC", "JEMF", "JEMP", "JEMS",
    "JEMT", "JEN", "JENC", "JENF", "JENP", "JENS", "JENT", "JEO", "JEOC", "JEOF", "JEOP",
    "JEOS", "JEOT", "JEP", "JEPC", "JEPF", "JEPP", "JEPS", "JEPT", "JEQ", "JEQC", "JEQF",
    "JEQP", "JEQS", "JEQT", "JER", "JERC", "JERF", "JERP", "JERS", "JERT", "JES", "JESC",
    "JESF", "JESP", "JESS", "JEST", "JET", "JETC", "JETF", "JETP", "JETS", "JETT", "JEU",
    "JEUC", "JEUF", "JEUP", "JEUS", "JEUT", "JEV", "JEVC", "JEVF", "JEVP", "JEVS", "JEVT",
    "JEW", "JEWC", "JEWF", "JEWP", "JEWS", "JEWT", "JEX", "JEXC", "JEXF", "JEXP", "JEXS",
    "JEXT", "JEY", "JEYC", "JEYF", "JEYP", "JEYS", "JEYT", "JEZ", "JEZC", "JEZF", "JEZP",
    "JEZS", "JEZT", "JF", "JFA", "JFAC", "JFAF", "JFAP", "JFAS", "JFAT", "JFB", "JFBC",
    "JFBF", "JFBP", "JFBS", "JFBT", "JFC", "JFCC", "JFCF", "JFCP", "JFCS", "JFCT", "JFD",
    "JFDC", "JFDF", "JFDP", "JFDS", "JFDT", "JFE", "JFEC", "JFEF", "JFEP", "JFES", "JFET",
    "JFF", "JFFC", "JFFF", "JFFP", "JFFS", "JFFT", "JFG", "JFGC", "JFGF", "JFGP", "JFGS",
    "JFGT", "JFH", "JFHC", "JFHF", "JFHP", "JFHS", "JFHT", "JFI", "JFIC", "JFIF", "JFIP",
    "JFIS", "JFIT", "JFJ", "JFJC", "JFJF", "JFJP", "JFJS", "JFJT", "JFK", "JFKC", "JFKF",
    "JFKP", "JFKS", "JFKT", "JFL", "JFLC", "JFLF", "JFLP", "JFLS", "JFLT", "JFM", "JFMC",
    "JFMF", "JFMP", "JFMS", "JFMT", "JFN", "JFNC", "JFNF", "JFNP", "JFNS", "JFNT", "JFO",
    "JFOC", "JFOF", "JFOP", "JFOS", "JFOT", "JFP", "JFPC", "JFPF", "JFPP", "JFPS", "JFPT",
    "JFQ", "JFQC", "JFQF", "JFQP", "JFQS", "JFQT", "JFR", "JFRC", "JFRF", "JFRP", "JFRS",
    "JFRT", "JFS", "JFSC", "JFSF", "JFSP", "JFSS", "JFST", "JFT", "JFTC", "JFTF", "JFTP",
    "JFTS", "JFTT", "JFU", "JFUC", "JFUF", "JFUP", "JFUS", "JFUT", "JFV", "JFVC", "JFVF",
    "JFVP", "JFVS", "JFVT", "JFW", "JFWC", "JFWF", "JFWP", "JFWS", "JFWT", "JFX", "JFXC",
    "JFXF", "JFXP", "JFXS", "JFXT", "JFY", "JFYC", "JFYF", "JFYP", "JFYS", "JFYT", "JFZ",
    "JFZC", "JFZF", "JFZP", "JFZS", "JFZT",
]

# Convert to .BK format
ALL_SET_STOCKS_BK = sorted([s + ".BK" for s in ALL_SET_STOCKS if s])
SECTORS = {
    "พลังงาน/สาธารณูปโภค": ["PTT", "PTTEP", "GULF", "GPSC", "BGRIM", "EGCO", "RATCH",
                            "BANPU", "TOP", "IRPC", "BCP", "OR", "SPRC", "EA"],
    "ธนาคาร/การเงิน": ["KBANK", "SCB", "BBL", "KTB", "TISCO", "KKP", "TTB",
                       "MTC", "SAWAD", "TIDLOR", "KTC", "AEONTS", "BLA"],
    "เทคโนโลยี/สื่อสาร": ["ADVANC", "INTUCH", "TRUE", "DELTA", "HANA", "KCE"],
    "พาณิชย์/บริการ": ["CPALL", "CPAXT", "HMPRO", "CRC", "COM7", "BJC", "GLOBAL", "DOHOME"],
    "ท่องเที่ยว/ขนส่ง": ["AOT", "BEM", "BTS", "MINT", "CENTEL", "ERW"],
    "โรงพยาบาล": ["BDMS", "BH", "BCH", "CHG", "PR9"],
    "เกษตร/อาหาร": ["CPF", "TU", "GFPT", "CBG", "OSP", "TVO", "NER", "ITC"],
    "อุตสาหกรรม/ปิโตรเคมี": ["SCC", "SCGP", "PTTGC", "IVL", "SCCC", "TASCO", "AH", "SAT"],
    "อสังหา/รับเหมา": ["LH", "AP", "SPALI", "QH", "ORI", "SIRI", "PSH",
                       "WHA", "AMATA", "STEC", "CK", "TPIPL"],
}

# DR (Depositary Receipt) บนตลาดหลักทรัพย์ไทย ที่อ้างอิงหุ้นบริษัทสัญชาติอเมริกันแท้ๆ เท่านั้น
# (คัดออก: ASML/เนเธอร์แลนด์, Ferrari/เนเธอร์แลนด์, On Holding/สวิส, Spotify/ลักเซมเบิร์ก,
#  Uniqlo-Fast Retailing/ญี่ปุ่น, Miniso/จีน — แม้จะมี DR ในไทยแต่ไม่ใช่บริษัทอเมริกัน)
# เลือกมาแค่ 1 DR series ต่อ 1 บริษัท (ราคาเคลื่อนไหวตามหุ้นแม่เหมือนกันไม่ว่าจะ series ไหน)
US_DR_STOCKS = [
    "AAPL80", "ABBV19", "ADBE06", "AMD80", "AMZN80", "AVGO80", "BAC03", "BDX06", "BKNG80",
    "BRKB80", "COSTCO19", "CRM01", "CRWD80", "CSCO06", "DELL19", "DISNEY19", "ESTEE80",
    "GOOG80", "GOOGL01", "GSUS06", "HOOD06", "ISRG01", "JNJ03", "JPMUS06", "KO80", "LLY80",
    "LULU06", "MA80", "META80", "MICRON01", "MNST06", "MS06", "NDAQ06", "NFLX80", "NIKE80",
    "NVDA80", "ORCL01", "PANW80", "PEP80", "PFIZER19", "PLTR01", "RBLX06", "SBUX80", "SNOW06",
    "TSLA80", "UBER06", "UNH19", "VISA80",
]

# DR บนตลาดหลักทรัพย์ไทย ที่อ้างอิงหุ้นบริษัท "ไม่ใช่สัญชาติอเมริกัน" (แม้จะซื้อขายในตลาด US
# หรือมีชื่อเสียงระดับโลกก็ตาม) — แยกกลุ่มจาก US_DR_STOCKS ตามที่ขอเพิ่ม
NON_US_DR_STOCKS = [
    "ASML01",     # ASML Holding — เนเธอร์แลนด์
    "FERRARI80",  # Ferrari — เนเธอร์แลนด์ (จดทะเบียน NV แม้สำนักงานใหญ่อิตาลี)
    "ONON03",     # On Holding — สวิตเซอร์แลนด์
    "SPOT06",     # Spotify — ลักเซมเบิร์ก
    "UNIQLO80",   # Fast Retailing (Uniqlo) — ญี่ปุ่น
    "MNSO80",     # Miniso — จีน
    "MELI06",     # MercadoLibre — อุรุกวัย/ละตินอเมริกา (จดทะเบียนที่ Delaware แต่ธุรกิจหลักละตินอเมริกา)
]

# หุ้นอเมริกันจริง ซื้อขายที่ตลาด US โดยตรง (ไม่ผ่าน DR ไทย) — ใช้ ticker เปล่าไม่มี .BK
# ใช้สแกนทั้งกลุ่มได้เหมือน SET100 แต่เทียบเทรนด์กับ SPY (S&P500 ETF) แทน SET Index
US_STOCKS = [
    "AAPL", "MSFT", "JPM", "V", "PG", "UNH", "HD", "MRK", "KO", "CSCO",
    "CVX", "MCD", "CRM", "WMT", "AXP", "IBM", "GS", "CAT", "HON", "AMGN",
    "BA", "MMM", "TRV", "JNJ", "DIS", "NKE", "VZ", "DOW", "INTC",
    "GOOGL", "AMZN", "META", "NVDA", "XOM", "PFE", "T", "COST", "PEP", "ADBE",
    "DKS", "RH", "WSM", "ULTA", "DECK", "CROX", "FIVE", "BURL", "YETI",
    "ETSY", "WING", "CAKE", "PLNT", "TXT", "CHRW", "HUN", "JBLU", "GNTX",
    "POOL", "FOXF", "OMCL", "MASI", "BLKB", "SAM", "RRC", "CIEN", "ZBRA", "ENPH",
    "FSLR", "CRSP", "EXPE", "NCLH", "RCL", "CCL", "LULU", "DPZ", "CMG", "WEN",
]
US_MARKET_INDEX = "SPY"  # ใช้แทน SET Index สำหรับกรอง "เทรนด์ตลาดใหญ่" ตอนสแกนหุ้น US


def get_market_type(symbol):
    """แยก market type จาก symbol: 'Regular' (SET/mai) หรือ 'DR/Foreign' (special segments)"""
    sym_clean = symbol.replace(".BK", "")
    if sym_clean:
        # Check last character
        last_char = sym_clean[-1]
        # ถ้า ending เป็น lowercase → DR/Foreign market
        if last_char.islower():
            return "DR/Foreign"
        else:
            return "Regular"
    return "Regular"


def get_all_set_stocks():
    """ดึงรายชื่อหุ้น SET ทั้งหมดจาก investpy (ประมาณ 900+ หุ้น) หรือ fallback ใช้ ALL_SET_STOCKS"""
    import streamlit as st

    @st.cache_data(ttl=86400, show_spinner=False)
    def _fetch_stocks():
        try:
            import investpy
            stocks_df = investpy.stocks.get_stocks(country='Thailand')
            symbols = stocks_df['symbol'].tolist()
            # เติม .BK และ filter ให้เหลือแค่สัญลักษณ์ที่มีค่า
            return sorted([s + ".BK" for s in symbols if s and len(s) > 0])
        except Exception as e:
            print(f"Error fetching SET stocks from investpy: {e}")
            # Fallback 1: ใช้ ALL_SET_STOCKS list (เตรียมไว้ ~800 หุ้น)
            if ALL_SET_STOCKS_BK:
                print(f"Using fallback list with {len(ALL_SET_STOCKS_BK)} stocks")
                return ALL_SET_STOCKS_BK
            # Fallback 2: ใช้ SET100 ถ้า all_set_stocks_bk ว่าง
            syms = sorted({s for lst in SECTORS.values() for s in lst})
            print(f"Using SET100 fallback with {len(syms)} stocks")
            return [s + ".BK" for s in syms]

    return _fetch_stocks()


def is_us_group(group):
    """True ถ้ากลุ่มที่เลือกเป็นหุ้น US จริง (ต้องใช้ SPY แทน SET Index เป็นตัวกรองเทรนด์ตลาดใหญ่)"""
    return group == "US100 (หุ้นอเมริกาจริง)"


def group_symbols(group):
    """คืน list สัญลักษณ์ (เติม .BK) ของกลุ่มที่เลือก · 'SET100' = รวม 80+ · 'SET Index' = ทุกหุ้น SET ~900+"""
    if group == "SET100 (ทั้งหมด)":
        syms = sorted({s for lst in SECTORS.values() for s in lst})
        return [s + ".BK" for s in syms]
    elif group == "SET Index":
        return get_all_set_stocks()  # ดึงทุกหุ้นใน SET
    elif group == "DR หุ้นอเมริกา (มีใน SET)":
        return [s + ".BK" for s in US_DR_STOCKS]
    elif group == "US100 (หุ้นอเมริกาจริง)":
        return list(US_STOCKS)  # ไม่เติม .BK — ticker US จริง
    elif group == "DR หุ้นต่างชาติอื่นๆ (ไม่ใช่อเมริกา)":
        return [s + ".BK" for s in NON_US_DR_STOCKS]
    else:
        syms = SECTORS.get(group, [])
        return [s + ".BK" for s in syms]
